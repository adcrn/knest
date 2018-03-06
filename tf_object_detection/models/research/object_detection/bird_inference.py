import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile

import matplotlib
matplotlib.use('Agg')

from collections import defaultdict
from io import StringIO
from matplotlib import pyplot as plt
from PIL import Image
from utils import label_map_util
from utils import visualization_utils as vis_util

def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)

MODEL_NAME = 'faster_rcnn_nas_coco_2018_01_28'

# Path to frozen detection graph. This is the actual model that is used for the object detection.
PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join('training', 'bird_object_detection.pbtxt')

NUM_CLASSES = 1

detection_graph = tf.Graph()
with detection_graph.as_default():
  od_graph_def = tf.GraphDef()
  with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
    serialized_graph = fid.read()
    od_graph_def.ParseFromString(serialized_graph)
    tf.import_graph_def(od_graph_def, name='')

label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)

# For the sake of simplicity we will use only 2 images:
# image1.jpg
# image2.jpg
# If you want to test the code with your images, just add path to the images to the TEST_IMAGE_PATHS.
PATH_TO_TEST_IMAGES_DIR = 'test_images'
TEST_IMAGE_PATHS = [ os.path.join(PATH_TO_TEST_IMAGES_DIR, 'image{}.jpg'.format(i)) for i in range(1, 2) ]

# Size, in inches, of the output images.
IMAGE_SIZE = (12, 8)

def run_inference_for_single_image(image, graph):
  with graph.as_default():
    with tf.Session() as sess:
      # Get handles to input and output tensors
      ops = tf.get_default_graph().get_operations()
      all_tensor_names = {output.name for op in ops for output in op.outputs}
      tensor_dict = {}
      for key in [
          'num_detections', 'detection_boxes', 'detection_scores',
          'detection_classes', 'detection_masks'
      ]:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
          tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
              tensor_name)
      if 'detection_masks' in tensor_dict:
        # The following processing is only for single image
        detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
        detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
        # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
        real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
        detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
        detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
        detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
            detection_masks, detection_boxes, image.shape[0], image.shape[1])
        detection_masks_reframed = tf.cast(
            tf.greater(detection_masks_reframed, 0.5), tf.uint8)
        # Follow the convention by adding back the batch dimension
        tensor_dict['detection_masks'] = tf.expand_dims(
            detection_masks_reframed, 0)
      image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

      # Run inference
      output_dict = sess.run(tensor_dict,
                             feed_dict={image_tensor: np.expand_dims(image, 0)})

      # all outputs are float32 numpy arrays, so convert types as appropriate
      output_dict['num_detections'] = int(output_dict['num_detections'][0])
      output_dict['detection_classes'] = output_dict[
          'detection_classes'][0].astype(np.uint8)
      output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
      output_dict['detection_scores'] = output_dict['detection_scores'][0]
      if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
  return output_dict

file_name = r'0{0:02d}.jpg'
count = 0

for image_path in TEST_IMAGE_PATHS:
	image = Image.open(image_path)
	image_width, image_height = image.size
	# The array based representation of the image will be used later in order to prepare the
	# result image with boxes and labels on it.
	image_np = load_image_into_numpy_array(image)
	# Expand dimensions since the model expects images to have shape: [1, None, None, 3]
	image_np_expanded = np.expand_dims(image_np, axis=0)
	# Actual detection
	output_dict = run_inference_for_single_image(image_np, detection_graph)
	# Visualization of the results of a detection
	vis_util.visualize_boxes_and_labels_on_image_array(
		image_np,
		output_dict['detection_boxes'],
		output_dict['detection_classes'],
		output_dict['detection_scores'],
		category_index,
		instance_masks=output_dict.get('detection_masks'),
		use_normalized_coordinates=True,
		line_thickness=8)
	# Get detection boxes as [N, 4]
	boxes = np.squeeze(output_dict['detection_boxes'])
	rows = boxes.shape[0]
	# Iterate through bounding boxes
	for i in range(0, rows):
	  # If the coords are all 0 stop processing this ndarray
	  if boxes[i,0] == 0 and boxes[i,1] == 0 and boxes[i,2] == 0 and boxes[i,3] == 0:
	    break

	  # Grab the normalized coordinates and convert them to coordinates that make sense for the entire image
	  ymin = boxes[i,0] * image_height
	  xmin = boxes[i,1] * image_width
	  ymax = boxes[i,2] * image_height
	  xmax = boxes[i,3] * image_width
	  ymin = ymin.astype('int64')
	  xmin = xmin.astype('int64')
	  ymax = ymax.astype('int64')
	  xmax = xmax.astype('int64')
	  # Crop the image 
	  cropped_image = tf.image.crop_to_bounding_box(image, ymin, xmin, ymax - ymin, xmax - xmin)
	  # Start a tf session to parse the image data
	  sess = tf.Session()
	  cropped_image_data = sess.run(cropped_image)
	  sess.close()
	  # Create figure from the cropped image
	  plt.figure(figsize=IMAGE_SIZE)
	  plt.imshow(cropped_image_data)
	  # Store the cropped image
	  plt.savefig("cropped_bboxes/" + file_name.format(count), format='jpg')
	  plt.clf()
	  count += 1
	  
	# Below is for bounding box stuff
	# Create figure
	#plt.figure(figsize=IMAGE_SIZE)
	#plt.imshow(image_np)
	# Save the current figure
	#plt.savefig("cropped_bboxes/" + "withregion.jpg")
	# Clear the current figure for the next iteration
	#plt.clf()
