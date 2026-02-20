import os
import asyncio
import io
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def verify_user_pattern():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Check if 'responses' exists
    if hasattr(client, "responses"):
        print("Found client.responses")
    elif hasattr(client, "beta") and hasattr(client.beta, "responses"):
        print("Found client.beta.responses")
    else:
        print("client.responses not found. Available attributes:", [a for a in dir(client) if not a.startswith("_")])
        # Force check if it's dynamic or newer
        try:
            print("Attempting to access client.responses...")
            _ = client.responses
            print("Successfully accessed client.responses")
        except AttributeError:
            print("Failed to access client.responses")

    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    print(f"Uploading {file_path} with purpose='assistants'...")
    with open(file_path, "rb") as f:
        # User said: purpose='assistants' even for this API
        file_obj = await client.files.create(file=f, purpose="assistants")
    
    print(f"File uploaded. ID: {file_obj.id}")
    
    try:
        print("Calling client.responses.create...")
        # Note: If client.responses doesn't exist, this will fail. 
        # But if the user says it works, maybe it's a newer version or private.
        
        # User pattern:
        # response = client.responses.create(
        #     model="gpt-5-nano-2025-08-07",
        #     input=[...]
        #     text={"format": {"type": "json_object"}}
        # )
        
        # I'll try to call it dynamically if it's not in dir()
        responses_api = getattr(client, "responses", None)
        if responses_api is None:
            responses_api = getattr(client.beta, "responses", None)

        if responses_api is None:
            print("Skipping call as API is not found.")
            return

        response = await responses_api.create(
            model="gpt-5-nano-2025-08-07",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Extraia o número da nota em JSON."},
                        {"type": "input_file", "file_id": file_obj.id}
                    ]
                }
            ],
            text={"format": {"type": "json_object"}}
        )
        print("Success!")
        print(response)
    except Exception as e:
        print(f"Failed to call Responses API: {str(e)}")
    finally:
        print(f"Deleting file {file_obj.id}...")
        await client.files.delete(file_obj.id)

if __name__ == "__main__":
    asyncio.run(verify_user_pattern())
