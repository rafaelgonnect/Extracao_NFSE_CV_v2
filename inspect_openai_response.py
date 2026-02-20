import os
import asyncio
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def inspect_response_structure():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    print(f"Uploading {file_path}...")
    with open(file_path, "rb") as f:
        file_obj = await client.files.create(file=f, purpose="assistants")
    
    try:
        print("Calling client.responses.create...")
        response = await client.responses.create(
            model="gpt-5-nano-2025-08-07",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Extract 'numero_nota' in JSON."},
                        {"type": "input_file", "file_id": file_obj.id}
                    ]
                }
            ],
            text={"format": {"type": "json_object"}}
        )
        
        print("\n--- RESPONSE OBJECT TYPE ---")
        print(type(response))
        
        print("\n--- RESPONSE ATTRIBUTES ---")
        print([a for a in dir(response) if not a.startswith("_")])
        
        print("\n--- RESPONSE DICT (if available) ---")
        try:
            print(json.dumps(response.model_dump(), indent=2))
        except:
            print(response)

        if hasattr(response, "choices"):
            print("\n--- CHOICE[0] ---")
            print(response.choices[0])
            if hasattr(response.choices[0], "message"):
                print("\n--- MESSAGE CONTENT ---")
                print(response.choices[0].message.content)

        if hasattr(response, "output"):
            print("\n--- OUTPUT ---")
            print(response.output)

    except Exception as e:
        print(f"Failed: {str(e)}")
    finally:
        await client.files.delete(file_obj.id)

if __name__ == "__main__":
    asyncio.run(inspect_response_structure())
