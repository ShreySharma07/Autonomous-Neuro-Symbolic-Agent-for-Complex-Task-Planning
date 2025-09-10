import os
from google import genai
from world_api2 import KitchenWorld
import json
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key = os.getenv("GOOGLE_API_KEY"))

prompt_template = """
You are a meticulous and logical kitchen assistant. Your goal is to complete the task by calling the available functions one step at a time. Do not perform actions that are not on this list.

# OVERALL GOAL
Your goal is to: Make a grilled cheese sandwich.

# AVAILABLE FUNCTIONS
- `look_around()`: Describes all objects in your current room and their locations.
- `get_object_info(object_name)`: Gets the properties of a specific object.
- `go_to(location_name)`: Moves you to a specific location (e.g., 'Counter', 'Fridge').
- `pickup(object_name)`: Picks up an object. You can only hold one object at a time.
- `put_down(location_name)`: Puts down the object you are currently holding in a specific location.
# For simplicity, we are not implementing use_object and finish_task in this step.

# OUTPUT FORMAT
You must respond in a valid JSON format. Your response should contain two keys: "thought" and "action".
- "thought": A brief, one-sentence explanation of your reasoning for the chosen action.
- "action": The exact function call you want to execute, for example: `pickup('Knife')`

#Strategy Hint
A good strategy is to first gather all necessary ingredients (2 breads slice, 1 cheese slice, butter) and tools (knife, pan, plate) intor one location like the counter before you start assemblying or cooking.

# HISTORY OF ACTIONS
{history}

# CURRENT OBSERVATION
Observation: {observation}
Inventory: {inventory}

# YOUR DECISION
Based on the history and your current observation, what is your next thought and action in JSON format?
"""

def parse_action(action_str):
    try:
        name, args_str = action_str.split('(',1)

        args_str = args_str.split(')',1)[0]

        args = [arg.strip().strip("'\"") for arg in args_str.split(',')]

        if args == ['']:
            args = []
        return name, args
    except ValueError:
        return None, None

if __name__=='__main__':

    world = KitchenWorld('neo4j://127.0.0.1:7687', 'neo4j', '***REDACTED***')

    chat = client.chats.create(model='Gemini 2.0 Flash-Lite')

    history = []

    max_step = 20

    for i in range(max_step):

        observation = world.look_around()
        inventory = world.get_inventory()
        print(f'Observation: {observation}\n')
        print(f'Inventory: {inventory}\n')

        # 2. Format the prompt
        history_str = '\n'.join(history)
        prompt = prompt_template.format(history=history_str, observation=observation, inventory=inventory)

        response_text = chat.send_message(prompt).text

        #4. parse the llm response in json
        try:
            if response_text.startswith("```"):
                response_text = response_text.strip("`").strip()
                # Also handle language hint like ```json
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()
            response_json = json.loads(response_text)
            thought = response_json['thought']
            action_str = response_json['action']
            print(f"Thought: {thought}\n")
            print(f"Action: {action_str}\n")
        except (json.JSONDecodeError, KeyError) as e:
            print(f'Error parsing LLM response: {e}')
            print(f'LLM response: {response_text}')
            break

        func_names, args = parse_action(action_str)

        if hasattr(world, func_names):
            func = getattr(world, func_names)
            result = func(*args)
        else:
            result = f"Error: Unknown function '{func_names}'"

        # 6. Update history and check for finish
        history.append(f"Step {i+1}: {action_str} -> {result}")
    
    # Clean up
    world.close()
    print("\n--- Loop finished ---")