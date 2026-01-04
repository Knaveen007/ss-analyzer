from PIL import Image, ImageDraw, ImageFont

def create_image():
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # Draw some text
    text = """
    PROJECT STATUS: DEPLOYMENT READY
    
    Status: Green
    Time: 2 Hours Remaining
    
    Checklist:
    [x] Code Verified
    [x] Zero Cost API Configured
    [x] CLI Tool Built
    """
    try:
        # data-science-types or similar might not be installed, using default load
        # For reliability, just use default font if specific ttf fails
        font = ImageFont.load_default() 
        # Scale isn't great on default font, but it works for OCR testing
    except:
        pass

    d.text((50,50), text, fill=(0,0,0))
    
    filename = "production_test_image.png"
    img.save(filename)
    print(f"✅ Created {filename}")

if __name__ == "__main__":
    create_image()
