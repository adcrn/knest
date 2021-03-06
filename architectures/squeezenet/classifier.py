# UCF Senior Design 2017-18
# Group 38

import numpy as np
import tflearn

OUTPUT_FOLDER = 'output/'


class ClassificationModel(object):
    """
    A model for object classification.
    """

    def __init__(self, image_size, weights, num_classes):
        self.network = self._build_network(image_size, num_classes)
        self.model = tflearn.DNN(self.network, checkpoint_path=OUTPUT_FOLDER,
                                 max_checkpoints=10, tensorboard_verbose=3,
                                 clip_gradients=0.)
        self.model.load(weights, weights_only=True)

    def _fire_module(self, input_layer, fire_layer_id, squeeze=16, expand=64):
        """
        The Fire module from the original SqueezeNet paper.
            input_layer:    (Tensor) preceding layers of network
            fire_layer_id:  (Integer) used to differentiate layers
            squeeze:        (Integer) filter size for the 'squeeze' part of module
            expand:         (Integer) filter size for the 'expand' part of module
        """

        layer_id = 'fire' + str(fire_layer_id) + '/'

        fire = tflearn.layers.conv.conv_2d(input_layer, squeeze, 1,
                                           padding='valid', activation='elu',
                                           weights_init='xavier',
                                           name=layer_id + "elu_" + "squeeze1x1")

        left = tflearn.layers.conv.conv_2d(fire, expand, 1,
                                           padding='valid', activation='elu',
                                           weights_init='xavier',
                                           name=layer_id + "elu_" + "expand1x1")

        right = tflearn.layers.conv.conv_2d(fire, expand, 3,
                                            padding='same', activation='elu',
                                            weights_init='xavier',
                                            name=layer_id + "elu_" + "expand3x3")

        out = tflearn.layers.merge_ops.merge([left, right], 'concat',
                                             axis=3, name=layer_id + 'merge')

        return out

    def _build_network(self, image_size, num_classes):
        """
            Build the SqueezeNet architecture.
                image_size:     (Tuple) size of image in form (width, height)
                num_classes:    (Integer) number of classes to be classified
        """

        # Start the network with an input layer of custom image size.
        net = tflearn.input_data(shape=[None, image_size[0], image_size[1], 3])

        net = tflearn.layers.conv.conv_2d(net, 64, 3, strides=2,
                                          padding='valid', activation='elu',
                                          weights_init='xavier',
                                          name='conv1')
        net = tflearn.layers.conv.max_pool_2d(net, 3, strides=2, name='pool1')

        net = self._fire_module(net, fire_layer_id=2, squeeze=16, expand=64)
        net = self._fire_module(net, fire_layer_id=3, squeeze=16, expand=64)
        net = tflearn.layers.conv.max_pool_2d(net, 3, strides=2, name='pool3')

        net = self._fire_module(net, fire_layer_id=4, squeeze=32, expand=128)
        net = self._fire_module(net, fire_layer_id=5, squeeze=32, expand=128)
        net = tflearn.layers.conv.max_pool_2d(net, 3, strides=2, name='pool5')

        net = self._fire_module(net, fire_layer_id=6, squeeze=48, expand=192)
        net = self._fire_module(net, fire_layer_id=7, squeeze=48, expand=192)
        net = self._fire_module(net, fire_layer_id=8, squeeze=64, expand=256)
        net = self._fire_module(net, fire_layer_id=9, squeeze=64, expand=256)
        net = tflearn.layers.core.dropout(net, 0.5, name='dropout9')

        net = tflearn.layers.conv.conv_2d(net, num_classes, 1, padding='valid',
                                          activation='elu', name='conv10')
        net = tflearn.layers.conv.global_avg_pool(net)

        net = tflearn.activations.softmax(net)

        nesterov = tflearn.optimizers.Nesterov(learning_rate=0.001, lr_decay=0.96, decay_step=100)
        net = tflearn.layers.estimator.regression(net, optimizer=nesterov)

        return net

    def predict(self, image):
        """
        Wraps the TFLearn model prediction function. Returns the
        predicted probabilites in an array.
            image: (ndarray) array representation of the image
        """
        return self.model.predict([image])

    def classify(self, prediction):
        """
        Determines whether an image contains a bird. Returns a boolean.
            prediction: (array) an array holding percent estimates of how
                        likely or unlikely that a bird is in the image
        """
        # if the first index has the higher percentage, there is a bird
        is_bird = np.argmax(prediction[0]) == 0
        return is_bird
