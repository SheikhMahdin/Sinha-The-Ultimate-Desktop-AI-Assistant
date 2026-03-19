import asyncio
from random import randint
from PIL import Image
import requests
from dotenv import get_key
import os
from time import sleep

# Function to open and display images based on a given prompt
def open_images(prompt):
    folder_path = r"Data"
    prompt = prompt.replace(" ", "_")
        
    Files = [f"{prompt}{i}.jpg" for i in range(1, 5)]
    
    for jpg_file in Files:
        image_path = os.path.join(folder_path, jpg_file)

        try:
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            img.show()
            sleep(1)

        except IOError:
            print(f"Unable to open {image_path}")

# API details
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
api_key = get_key('.env', 'HuggingFaceAPIKey')
print(f"API Key loaded: {api_key[:10]}..." if api_key else "API Key: NOT FOUND!")
headers = {"Authorization": f"Bearer {api_key}"}

# Async function to send a query
async def query(payload):
    print(f"Sending request to API...")
    response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload)
    print(f"Response status code: {response.status_code}")
    print(f"Response length: {len(response.content)} bytes")
    
    # Check if response is an error
    if response.status_code != 200:
        print(f"ERROR Response: {response.text}")
    
    return response.content

# Async function to generate images
async def generate_images(prompt: str):
    os.makedirs("Data", exist_ok=True)
    tasks = []

    for i in range(4):
        print(f"Creating task {i+1}/4")
        payload = {
            "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution, seed={randint(0, 1000000)}",
        }
        task = asyncio.create_task(query(payload))
        tasks.append(task)

    print("Waiting for all tasks to complete...")
    image_bytes_list = await asyncio.gather(*tasks)

    print("Saving images...")
    for i, image_bytes in enumerate(image_bytes_list):
        filename = fr"Data\{prompt.replace(' ', '_')}{i + 1}.jpg"
        print(f"Saving to: {filename}, Size: {len(image_bytes)} bytes")
        with open(filename, "wb") as f:
            f.write(image_bytes)
        print(f"Saved {filename}")

def GenerateImages(prompt: str):
    print(f"Generation started for prompt: '{prompt}'")
    asyncio.run(generate_images(prompt))
    print("Generation complete, opening images...")
    open_images(prompt)

# Main loop
while True:
    try:
        with open(r"Frontend\Files\ImageGeneration.data", "r") as f:
            Data = f.read()
        
        print(f"Read from file: '{Data}'")

        parts = Data.split(",")
        if len(parts) != 2:
            print("Invalid data format")
            sleep(1)
            continue
            
        prompt = parts[0].strip()
        Status = parts[1].strip()
        
        print(f"Prompt: '{prompt}', Status: '{Status}'")

        if Status == "True":
            print("Generating Images ...")
            GenerateImages(prompt=prompt)

            with open(r"Frontend\Files\ImageGeneration.data", "w") as f:
                f.write("False,False")
            break
        else:
            print("Status is False, waiting...")
            sleep(1)

    except FileNotFoundError:
        print("File not found, creating...")
        os.makedirs(r"Frontend\Files", exist_ok=True)
        with open(r"Frontend\Files\ImageGeneration.data", "w") as f:
            f.write("False,False")
        sleep(1)
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sleep(1)