from flask import Flask, render_template, request,send_from_directory
import os
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
from keras.applications.vgg16 import preprocess_input
from keras.applications.vgg16 import decode_predictions
from PIL import Image
import tifffile as tiff  # To handle .tif files
from torchvision import transforms
import numpy as np
import torch
app = Flask(__name__)
# Load your segmentation model (assuming you have it saved)
# Replace this with the path to your saved model
model = torch.load('model.pth', map_location=torch.device('cpu'))
model.eval()  # Set model to evaluation mode

# Define the preprocessing transformation
preprocess = transforms.Compose([
    transforms.Resize((128, 128)),  # Resize to model input size
    transforms.ToTensor(),          # Convert to Tensor
])

@app.route('/', methods=['GET'])
def hello_word():
    return render_template('index.html')

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'images'), filename)



@app.route('/', methods=['POST'])
def predict():
    # Handle image upload
    imagefile = request.files['imagefile']
    image_path = "./images/TifImage/" + imagefile.filename
    imagefile.save(image_path)
    
    # Load the .tif image using tifffile (assuming it has 12 channels)
    tif_image = tiff.imread(image_path)  # Load the .tif file
    
    # Check the shape of the image (assuming last dimension is channels)
    print("Original image shape:", tif_image.shape)
    
    # Ensure the image has 12 channels and is in the expected format
    if tif_image.shape[-1] == 12:
        img_array = tif_image  # Use the image as is
    else:
        return "The image doesn't have 12 channels!"
    
    # Convert the NumPy array to a PyTorch tensor and adjust dimensions (C x H x W)
    img_tensor = torch.tensor(img_array, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)  # Add batch dimension
    
    # Perform inference
    with torch.no_grad():
        output = model(img_tensor)
        predictions = (torch.sigmoid(output) > 0.5).float()  # Apply sigmoid and threshold to get binary mask
    
    # Post-process the output (assuming the output is a segmentation mask)
    output_mask = predictions.squeeze(0).cpu().numpy()  # Get the mask in numpy format

    # Create an RGB image for visualization
    highlighted_image = np.zeros((output_mask.shape[1], output_mask.shape[2], 3), dtype=np.uint8)
    
    # Highlight the regions where output_mask is 1
    highlighted_image[output_mask[0] == 1] = [255, 255, 255]  # Red for detected regions
    highlighted_image[output_mask[0] == 0] = [0, 0, 0]    # Black for background

    # Convert the output mask to a PIL image and save it
    output_image_path = "./images/output_/" + imagefile.filename.replace('.tif', '_highlighted.png')
    output_mask_image = Image.fromarray(highlighted_image)  # Create an image from the highlighted mask
    output_mask_image.save(output_image_path)

    # Prepare result image path for rendering
    result_image = 'output_/' + imagefile.filename.replace('.tif', '_highlighted.png')
    return render_template('index.html', result_image=result_image)



if __name__ == '__main__':
    app.run(port=3000, debug=True)
