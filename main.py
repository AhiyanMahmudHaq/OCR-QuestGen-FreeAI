import os
import glob
import time
import base64
from anthropic import Anthropic

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
# Set your API key in your environment variables, e.g., export ANTHROPIC_API_KEY="sk-ant-..."
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Phone Camera Directory (Adjust if your Android path differs)
CAMERA_DIR = "/storage/emulated/0/DCIM/Camera"
PROCESSED_DIR = "/storage/emulated/0/DCIM/Camera/Processed_Notes"

# Rate Limiting Configuration for Free Tier (Requests Per Minute)
DELAY_BETWEEN_CALLS = 65 # Wait 65 seconds between API calls to stay safely under limits

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_latest_images(directory, count=3):
    """Finds the most recent image files in the directory."""
    search_pattern = os.path.join(directory, "*.[jJ][pP][gG]") # Add PNG if needed
    files = glob.glob(search_pattern)
    files.sort(key=os.path.getmtime, reverse=True)
    return files[:count]

def encode_image(image_path):
    """Encodes an image to base64 for Claude's Vision API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# ==========================================
# XML MASTER PROMPT
# ==========================================
MASTER_PROMPT = """
<prompt_configuration>
    <system_role>
        You are a rigorous, academic-level examiner and subject matter expert. Your goal is to analyze educational notes and resources from the provided image attachments, utilizing Adaptive Thinking to generate a standardized question paper and marking scheme.
    </system_role>
    <execution_steps>
        <step>
            <action>Adaptive Subject Detection</action>
            <description>Analyze the handwritten or printed text and diagrams in the provided images. Use your thinking budget to accurately identify the core subject, specific topics, and academic level.</description>
        </step>
        <step>
            <action>Question Generation</action>
            <description>Draft a balanced, challenging question paper. Include Multiple Choice Questions (MCQs), Short Answer Questions (SAQs), and Long/Essay Questions based strictly on the extracted concepts. Do not invent material outside the scope of the notes.</description>
        </step>
        <step>
            <action>Marking Scheme Creation</action>
            <description>Develop a comprehensive, step-by-step marking rubric for the generated questions. Highlight mandatory keywords, formulas, and logical steps required for a student to achieve full marks.</description>
        </step>
    </execution_steps>
    <output_format>
        Format your final response cleanly with markdown headers: 
        # [SUBJECT DETECTED: Insert Subject]
        ## QUESTION PAPER
        (List questions here)
        ## MARKING SCHEME
        (List detailed grading criteria here)
    </output_format>
</prompt_configuration>
"""

# ==========================================
# MAIN EXECUTION WORKFLOW
# ==========================================
def generate_study_material():
    ensure_dir(PROCESSED_DIR)
    
    print("🔍 Scanning camera directory for recent notes...")
    recent_images = get_latest_images(CAMERA_DIR, count=2) # Batching 2 images per request
    
    if not recent_images:
        print("No images found in the specified directory.")
        return

    # Construct the message content payload
    content_payload = []
    
    for img_path in recent_images:
        print(f"📸 Packing image: {os.path.basename(img_path)}")
        base64_data = encode_image(img_path)
        content_payload.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64_data,
            }
        })
    
    # Append the XML Master Prompt to the payload
    content_payload.append({
        "type": "text",
        "text": MASTER_PROMPT
    })

    print("🧠 Sending payload to Claude with Adaptive Thinking enabled...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6", # Swap to claude-4-5-sonnet if explicitly needed
            max_tokens=4096,
            thinking={
                "type": "enabled", 
                "budget_tokens": 2048 # Allocating token budget for adaptive reasoning
            },
            messages=[
                {
                    "role": "user",
                    "content": content_payload
                }
            ]
        )
        
        print("\n✅ Generation Complete!\n")
        print("="*50)
        print(response.content[0].text)
        print("="*50)
        
        # Move processed files to avoid re-reading them next cycle
        for img_path in recent_images:
            filename = os.path.basename(img_path)
            os.rename(img_path, os.path.join(PROCESSED_DIR, filename))
            
    except Exception as e:
        print(f"❌ Error during API call: {e}")

    print(f"⏳ Sleeping for {DELAY_BETWEEN_CALLS} seconds to respect Free Tier limits...")
    time.sleep(DELAY_BETWEEN_CALLS)

if __name__ == "__main__":
    # This is PURELY "VIBE-CODED" and this version is a prototype
    # In a real daemon/workflow, you'd wrap this in a while True loop. 
    # For safe vibe-coding, running it once per manual trigger is recommended first.
    generate_study_material()
