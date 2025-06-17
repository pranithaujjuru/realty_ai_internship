import os
import time
import hashlib
import requests
import json

# API Config
url_pre = "https://ap-east-1.tensorart.cloud"
api_key = "38dbb245-327b-485c-bfdf-63ae966edb73"
url_job = "/v1/jobs"
url_resource = "/v1/resource"
url_workflow = "/v1/workflows"

HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {api_key}'
}
def fetch_template(template_id):
    url = f"{url_pre}/v1/workflows/{template_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        print(f"Error fetching template: {err}")
        
        
def upload_img(img_path):
    print(f"Uploading image: {img_path}")
    if not os.path.exists(img_path):
        print(f"Error: File not found at {img_path}")
        return None

    data = {"expireSec": 3600}
    try:
        response = requests.post(f"{url_pre}{url_resource}/image", json=data, headers=HEADERS)
        response.raise_for_status()
        response_data = response.json()
        resource_id = response_data['resourceId']
        put_url = response_data['putUrl']
        headers_upload = response_data['headers']

        with open(img_path, 'rb') as f:
            upload_response = requests.put(put_url, data=f.read(), headers=headers_upload)
            upload_response.raise_for_status()

        print(f"Upload successful! Resource ID: {resource_id}")
        return resource_id
    except requests.exceptions.RequestException as e:
        print(f"Upload error: {e}")
        return None


def generate_field_attrs(template_json, resource_ids=None, positive_prompt=None):
    """
    Assigns each resource ID to an individual image field.
    If template has a list in fieldValue, it gets flattened.
    """
    field_attrs = []
    resource_ids = resource_ids or []
    image_index = 0

    for item in template_json.get("fields", {}).get("fieldAttrs", []):
        node_id = item.get("nodeId")
        field_name = item.get("fieldName")
        field_value = item.get("fieldValue")

        # Handle image assignment per field
        if "image" in field_name.lower():
            if image_index < len(resource_ids):
                field_value = resource_ids[image_index]
                image_index += 1
            else:
                field_value = ""  # leave empty if no image available

        # Handle prompt or text_positive
        if field_name in ["prompt", "text_positive"] and positive_prompt:
            field_value = positive_prompt
        if field_name=="width":
            field_value = 1920
        if field_name=="height":
            field_value = 1080


        field_attrs.append({
            "nodeId": node_id,
            "fieldName": field_name,
            "fieldValue": field_value
        })

    return field_attrs

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
    template_id = input("📝 Enter template ID: ").strip()
    source_img = input("🖼️ Enter path to source image: ").strip()
    r1 = upload_img(source_img)

    resource_ids = [r1] if r1 else []
    positive_prompt = None

    use_target = input("🎯 Do you want to provide a target image? (yes/no): ").strip().lower()
    if use_target in ['yes', 'y']:
        target_img = input("🖼️ Enter path to target image: ").strip()
        r2 = upload_img(target_img)
        if r2:
            resource_ids.append(r2)
    else:
        positive_prompt = input("💬 Enter a positive prompt: ").strip()

    template = fetch_template(template_id)
    if template:
        field_attrs = generate_field_attrs(template, resource_ids, positive_prompt)
        generate_image(resource_ids,template_id,field_attrs)
    else:
        print("❌ Template fetch failed.")



if __name__ == "__main__":
    main()
