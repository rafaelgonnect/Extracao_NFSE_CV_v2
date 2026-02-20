import os
import asyncio
import base64
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_document_type():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    print("Testing type: 'document'...")
    try:
        response = await client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract data."},
                    {"type": "document", "document": {"url": f"data:application/pdf;base64,{pdf_base64}"}}
                ]}
            ]
        )
        print("Success!")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_document_type())
