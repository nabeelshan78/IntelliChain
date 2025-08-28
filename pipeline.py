import os
import openai
import utils
from utils import *
import panel as pn
pn.extension()

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())   # read local .env file

openai.api_key  = os.environ['OPENAI_API_KEY']

def execute_step_1(user_input):
    response = openai.Moderation.create(input=user_input)
    return response["results"][0]["flagged"]

def execute_step_2(user_input):
    category_and_product_response = utils.find_category_and_product(user_input, utils.get_products_and_category())
    category_and_product_list = utils.read_string_to_list(category_and_product_response)
    return category_and_product_list


def execute_step_3(category_and_product_list):
    return utils.generate_output_string(category_and_product_list)


def execute_step_4(user_input, product_information, all_messages):
    delimiter = "```"
    
    system_message = f"""
    You are a customer service assistant for a large electronic store. \
    Your tone should be friendly, helpful, and natural.

    Use the 'Relevant product information' provided to answer the user's query. \
    For each specific product mentioned, write a short, engaging paragraph summarizing its key features, primary use, and price. \
    If the user asks about a general category, briefly describe the types of products available (e.g., "We offer a range of Xs from Ys to Zs").

    Your goal is to be informative but not overwhelming. Avoid just listing all the raw data fields. \
    Always end your response with a relevant follow-up question to guide the conversation.
    """
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f"{delimiter}{user_input}{delimiter}"},
        {'role': 'assistant', 'content': f"Relevant product information:\n{product_information}"}
    ]

    final_response = get_completion_from_messages(all_messages + messages)
    all_messages = all_messages + messages[1:]
    return final_response, all_messages



def execute_step_5(final_response):
    response = openai.Moderation.create(input=final_response)
    return response["results"][0]["flagged"]


def execute_step_6(user_input, product_information, final_response):
    system_message = f"""
    You are an assistant that evaluates whether \
    customer service agent responses sufficiently \
    answer customer questions, and also validates that \
    all the facts the assistant cites from the product \
    information are correct.
    The product information and user and customer \
    service agent messages will be delimited by \
    3 backticks, i.e. ```.
    Respond with a Y or N character, with no punctuation:
    Y - if the output sufficiently answers the question \
    AND the response correctly uses product information
    N - otherwise

    Output a single letter only.
    """
    
    user_message = f"""
    Customer message: ```{user_input}```
    Product information: ```{product_information}```
    Agent response: ```{final_response}```

    Does the response use the retrieved information correctly?
    Does the response sufficiently answer the question?

    Output Y or N
    """
    
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_message}
    ]
    
    return get_completion_from_messages(messages)



def execute_step_7(evaluation_response, final_response, debug):
    if "Y" in evaluation_response:
        if debug: print("Step 7: Model approved the response.\n\n")
        return final_response
    else:
        if debug: print("Step 7: Model disapproved the response.")
        neg_str = "I'm unable to provide the information you're looking for. I'll connect you with a human representative for further assistance."
        return neg_str
    



def process_user_message(user_input, all_messages, debug=True):
    delimiter = "```"
    
    # Step 1: Check input to see if it flags the Moderation API or is a prompt injection
    if execute_step_1(user_input):
        print("Step 1: Input flagged by Moderation API.")
        return "Sorry, we cannot process this request."
    if debug: print("Step 1: Input passed moderation check.")
        
    
    # Step 1: Get category and product list
    category_and_product_list = execute_step_2(user_input)
    if debug: print("Step 2: Extracted list of products.")
#     print(category_and_product_list)
#     print('='*100)

        
    # Step 3: If products are found, look them up
    product_information = execute_step_3(category_and_product_list)
    if debug: print("Step 3: Looked up product information.")
#     print(product_information)
#     print('='*100)

        
    # Step 4: Answer the user question
    final_response, all_messages = execute_step_4(user_input, product_information, all_messages)
    if debug:print("Step 4: Generated response to user question.")  
#     print(final_response)
#     print('='*100)
    

    # Step 5: Put the answer through the Moderation API
    if execute_step_5(final_response):
        if debug: print("Step 5: Response flagged by Moderation API.")
        return "Sorry, we cannot provide this information."
    if debug: print("Step 5: Response passed moderation check.")
        

    # Step 6: Ask the model if the response answers the initial user query well
    evaluation_response = execute_step_6(user_input, product_information, final_response)
    if debug: print("Step 6: Model evaluated the response.")
#     print(evaluation_response)
#     print('='*100)

        
    # Step 7: If yes, use this answer; if not, say that you will connect the user to a human
    final_response = execute_step_7(evaluation_response, final_response, debug)
    
    return final_response, all_messages


def run_pipeline(user_input, all_messages, debug=True):
    return process_user_message(user_input, all_messages, debug)