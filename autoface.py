import requests
import json
import os

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



'''

# ---------- Automation Flow Starts Here ----------
if __name__ == "__main__":
    # Choose any template
    template_id = "688362427502551075"
    positive_prompt = "A girl riding horse wearing black hoodie and blue jeans"

    # Upload images as needed (one or two, depending on the model)
    r1 = upload_img("source_image.jpg")
    r2 = upload_img("target_image.png")
    resource_ids = [r for r in [r1, r2] if r]  # filters out None

    # Fetch the selected workflow
    template = fetch_template(template_id)

    # Generate field attributes dynamically
    if template:
        field_attrs = generate_field_attrs(template, resource_ids,positive_prompt)
        print("Final fieldAttrs:", json.dumps(field_attrs, indent=2)) '''
