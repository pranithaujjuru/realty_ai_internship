import os
import time
import hashlib
import requests
import json
from autoface import generate_field_attrs

# API Details
url_pre = "https://ap-east-1.tensorart.cloud"
api_key = "38dbb245-327b-485c-bfdf-63ae966edb73"  # Replace with your actual API key
url_job = "/v1/jobs"
url_resource = "/v1/resource"
url_workflow = "/v1/workflows"

# Headers for API Key Authentication
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

def ensure_output_folder():
    """Ensure that the 'outputs' folder exists."""
    if not os.path.exists("outputs"):
        os.makedirs("outputs")

def save_image(image_url):
    """Download and save the generated image. Return the saved image path."""
    ensure_output_folder()
    response = requests.get(image_url)
    if response.status_code == 200:
        # Create a unique filename based on a hash of the URL
        image_path = os.path.join("outputs", f"{hashlib.md5(image_url.encode()).hexdigest()}.png")
        with open(image_path, "wb") as img_file:
            img_file.write(response.content)
        print(f"Image saved to {image_path}")
        return image_path
    else:
        print("Error downloading image.")
        return None

def get_job_result(job_id):
    """Poll the API for job completion status and return the output image path when complete."""
    while True:
        time.sleep(1)
        response = requests.get(f"{url_pre}{url_job}/{job_id}", headers=HEADERS)
        job_response = response.json()
        if 'job' in job_response:
            job_dict = job_response['job']
            job_status = job_dict.get('status')
            print("Job status:", job_dict)
            if job_status in ['SUCCESS', 'FAILED']:
                if job_status == 'SUCCESS':
                    image_url = job_dict['successInfo']['images'][0]['url']
                    print(f"Image URL: {image_url}")
                    print("Image generation successful.")
                    return save_image(image_url)
                else:
                    print("Image generation failed.")
                    return None

def upload_img(img_path):
    """Upload an image and return the resource ID."""
    print(f"Uploading image: {img_path}")
    data = {"expireSec": 3600}
    response = requests.post(f"{url_pre}{url_resource}/image", json=data, headers=HEADERS)
    print("Upload response:")
    print(response.text)
    response_data = response.json()
    resource_id = response_data['resourceId']
    put_url = response_data['putUrl']
    headers = response_data['headers']
    
    with open(img_path, 'rb') as f:
        res = f.read()
        upload_response = requests.put(put_url, data=res, headers=headers)
        print("PUT response:")
        print(upload_response.text)
    
    return resource_id


def fetch_template(template_id):
    url = f"{url_pre}/v1/workflows/{template_id}"
    headers = {
        'Authorization': f'Bearer {api_key}',
        "Accept": "application/json"
        
    }
    payload={}
    try:
        response = requests.request("GET",url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")      



def generate_image(resource_id ,template_id,field_attrs,positive_prompt=None,style=None,negative_prompt=None):
    """
    Submit a job using the predefined workflow template with template ID 688362427502551075.
    The style (and prompt) are provided as parameters.
    """
    data = {
        "request_id": hashlib.md5(str(int(time.time())).encode()).hexdigest(),
        "templateId": template_id,
        "params": {
            "async": False,
            "priority": "NORMAL",
            "extraParams": {}
        },
        "fields": {
            "fieldAttrs": field_attrs

        },
    }
    
    # Submit the job
    response = requests.post(f"{url_pre}{url_job}/workflow/template", json=data, headers=HEADERS)
    print("Template job submission response:")
    print(response.text)
    response_data = response.json()
    
    if 'job' in response_data:
        job_dict = response_data['job']
        job_id = job_dict.get('id')
        print(f"Workflow Job ID: {job_id}, Status: {job_dict.get('status')}")
        # Poll until the job is complete and then return the output image path
        return get_job_result(job_id)
    else:
        print("Failed to create workflow job:", response_data)
        return None




def main():
    template_id = input("Enter template_id of the workflow: ").strip()
    
    # Upload mandatory source image
    source_img = input("Enter path to source image (e.g., source_image.jpg): ").strip()
    r1 = upload_img(source_img)
    
    # Ask if user wants to provide a target image
    use_target = input("Do you want to provide a target image? (yes/no): ").strip().lower()

    resource_ids = [r1]
    positive_prompt = None

    if use_target in ["yes", "y"]:
        target_img = input("Enter path to target image (e.g., target_image.png): ").strip()
        r2 = upload_img(target_img)
        if r2:
            resource_ids.append(r2)
    else:
        # Ask for prompt if no second image
        positive_prompt = input("Enter a positive prompt for image generation: ").strip()

    # Fetch template JSON
    template = fetch_template(template_id)
    if isinstance(template, dict):
        field_attrs = generate_field_attrs(template, resource_ids, positive_prompt)
        # Generate image
        generate_image(resource_ids, template_id, field_attrs, positive_prompt)
    else:
        print("❌ Failed to fetch template JSON. Check API or token.")

if __name__=="__main__":
    main()