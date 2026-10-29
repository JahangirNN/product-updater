import os
import sys
import httpx
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql

PRODUCT_ID = "gid://shopify/Product/15886266794150"
OLD_MEDIA_ID = "gid://shopify/MediaImage/71085123371174"
IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "horizon_clean_theme", "assets", "checkcheck-square-seal.png")

def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: image not found at {IMAGE_PATH}")
        sys.exit(1)

    file_size = os.path.getsize(IMAGE_PATH)
    print(f"Uploading {IMAGE_PATH} (size: {file_size} bytes)")

    # 1. Staged upload create
    staged_mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    staged_input = [{
        "filename": "checkcheck-square-seal.png",
        "mimeType": "image/png",
        "httpMethod": "POST",
        "resource": "IMAGE",
        "fileSize": str(file_size)
    }]
    
    staged_res = execute_shopify_graphql(staged_mutation, {"input": staged_input})
    result_dict = staged_res[0]
    if "data" in result_dict:
        data = result_dict["data"].get("stagedUploadsCreate", {})
    else:
        data = result_dict.get("stagedUploadsCreate", {})
    user_errors = data.get("userErrors", [])
    if user_errors:
        print("Staged upload user errors:", user_errors)
        sys.exit(1)

    targets = data.get("stagedTargets", [])
    if not targets:
        print("No staged targets returned:", staged_res)
        sys.exit(1)

    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    parameters = {param["name"]: param["value"] for param in target["parameters"]}

    print(f"Uploading file to {upload_url}...")
    with open(IMAGE_PATH, "rb") as f:
        file_bytes = f.read()

    # Shopify staged upload multipart/form-data POST
    files = {"file": ("checkcheck-square-seal.png", file_bytes, "image/png")}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(upload_url, data=parameters, files=files)
        print(f"S3/GCS Upload HTTP status: {resp.status_code}")
        if resp.status_code not in (200, 201, 204):
            print("Upload failed:", resp.text)
            sys.exit(1)

    print(f"Uploaded successfully. Resource URL: {resource_url}")

    # 2. Attach media to product
    create_media_mutation = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          id
          status
        }
        mediaUserErrors {
          field
          message
        }
      }
    }
    """
    media_input = [{
        "mediaContentType": "IMAGE",
        "originalSource": resource_url,
        "alt": "Official CheckCheck Certificate of Authenticity"
    }]
    media_res = execute_shopify_graphql(create_media_mutation, {
        "productId": PRODUCT_ID,
        "media": media_input
    })
    print("Media creation response:", media_res)

    # 3. Delete old rectangular badge media
    delete_media_mutation = """
    mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
      productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
        deletedMediaIds
        mediaUserErrors {
          field
          message
        }
      }
    }
    """
    del_res = execute_shopify_graphql(delete_media_mutation, {
        "productId": PRODUCT_ID,
        "mediaIds": [OLD_MEDIA_ID]
    })
    print("Media deletion response:", del_res)

if __name__ == "__main__":
    main()
