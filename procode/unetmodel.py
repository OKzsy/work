#coding=utf-8
import keras
from keras.models import *
from keras.layers import *
from keras.layers.normalization import BatchNormalization
from keras.backend import binary_crossentropy
from keras import backend as K
from keras.optimizers import *

smooth = 1e-12

def jaccard_coef(y_true, y_pred):
    intersection = K.sum(y_true * y_pred, axis=[0, 1, 2])
    sum_ = K.sum(y_true + y_pred, axis=[0, 1, 2])

    jac = (intersection + smooth) / (sum_ - intersection + smooth)

    return K.mean(jac)


def jaccard_coef_int(y_true, y_pred):
    y_pred_pos = K.round(K.clip(y_pred, 0, -1))

    intersection = K.sum(y_true * y_pred_pos, axis=[0, 1, 2])
    sum_ = K.sum(y_true + y_pred_pos, axis=[0, 1, 2])

    jac = (intersection + smooth) / (sum_ - intersection + smooth)

    return K.mean(jac)


def jaccard_coef_loss(y_true, y_pred):
    return -K.log(jaccard_coef(y_true, y_pred)) + binary_crossentropy(y_pred, y_true)



def unet(n_label,img_sz,n_channels):
    inputs = Input((img_sz, img_sz,n_channels))

    conv1 = Conv2D(32, 3, activation='relu', padding='same')(inputs)
    conv1 = BatchNormalization(axis=-1)(conv1)
    conv1 = keras.layers.advanced_activations.ELU()(conv1)
    conv1 = Conv2D(32, 3, activation='relu',padding='same')(conv1)
    conv1 = BatchNormalization(axis=-1)(conv1)
    conv1 = keras.layers.advanced_activations.ELU()(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)

    conv2 = Conv2D(64, 3, activation='relu',padding='same')(pool1)
    conv2 = BatchNormalization(axis=-1)(conv2)
    conv2 = keras.layers.advanced_activations.ELU()(conv2)
    conv2 = Conv2D(64, 3, activation='relu',padding='same')(conv2)
    conv2 = BatchNormalization(axis=-1)(conv2)
    conv2 = keras.layers.advanced_activations.ELU()(conv2)
    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)

    conv3 = Conv2D(128, 3, activation='relu',padding='same')(pool2)
    conv3 = BatchNormalization(axis=-1)(conv3)
    conv3 = keras.layers.advanced_activations.ELU()(conv3)
    conv3 = Conv2D(128, 3, activation='relu',padding='same')(conv3)
    conv3 = BatchNormalization(axis=-1)(conv3)
    conv3 = keras.layers.advanced_activations.ELU()(conv3)
    pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)

    conv4 = Conv2D(256, 3, activation='relu',padding='same')(pool3)
    conv4 = BatchNormalization(axis=-1)(conv4)
    conv4 = keras.layers.advanced_activations.ELU()(conv4)
    conv4 = Conv2D(256, 3, activation='relu',padding='same')(conv4)
    conv4 = BatchNormalization(axis=-1)(conv4)
    conv4 = keras.layers.advanced_activations.ELU()(conv4)
    pool4 = MaxPooling2D(pool_size=(2, 2))(conv4)

    conv5 = Conv2D(512, 3, activation='relu',padding='same')(pool4)
    conv5 = BatchNormalization(axis=-1)(conv5)
    conv5 = keras.layers.advanced_activations.ELU()(conv5)
    conv5 = Conv2D(512, 3, activation='relu',padding='same')(conv5)
    conv5 = BatchNormalization(axis=-1)(conv5)
    conv5 = keras.layers.advanced_activations.ELU()(conv5)

    # up6 = merge([UpSampling2D(size=(2, 2))(conv5), conv4], mode='concat', concat_axis=3)
    up6 = concatenate([UpSampling2D(size=(2, 2))(conv5), conv4],axis=3)
    conv6 = Conv2D(256, 3, activation='relu',padding='same')(up6)
    conv6 = BatchNormalization(axis=-1)(conv6)
    conv6 = keras.layers.advanced_activations.ELU()(conv6)
    conv6 = Conv2D(256, 3, activation='relu',padding='same')(conv6)
    conv6 = BatchNormalization(axis=-1)(conv6)
    conv6 = keras.layers.advanced_activations.ELU()(conv6)

    # up7 = merge([UpSampling2D(size=(2, 2))(conv6), conv3], mode='concat', concat_axis=1)
    up7 = concatenate([UpSampling2D(size=(2, 2))(conv6), conv3],axis=3)
    conv7 = Conv2D(128, 3, activation='relu',padding='same')(up7)
    conv7 = BatchNormalization(axis=-1)(conv7)
    conv7 = keras.layers.advanced_activations.ELU()(conv7)
    conv7 = Conv2D(128, 3, activation='relu',padding='same')(conv7)
    conv7 = BatchNormalization(axis=-1)(conv7)
    conv7 = keras.layers.advanced_activations.ELU()(conv7)

    # up8 = merge([UpSampling2D(size=(2, 2))(conv7), conv2], mode='concat', concat_axis=1)
    up8 = concatenate([UpSampling2D(size=(2, 2))(conv7), conv2],axis=3)
    conv8 = Conv2D(64, 3, activation='relu',padding='same')(up8)
    conv8 = BatchNormalization(axis=-1)(conv8)
    conv8 = keras.layers.advanced_activations.ELU()(conv8)
    conv8 = Conv2D(64, 3, activation='relu',padding='same')(conv8)
    conv8 = BatchNormalization(axis=-1)(conv8)
    conv8 = keras.layers.advanced_activations.ELU()(conv8)

    # up9 = merge([UpSampling2D(size=(2, 2))(conv8), conv1], mode='concat', concat_axis=1)
    up9 = concatenate([UpSampling2D(size=(2, 2))(conv8), conv1], axis=3)
    conv9 = Conv2D(32, 3, activation='relu',padding='same')(up9)
    conv9 = BatchNormalization(axis=-1)(conv9)
    conv9 = keras.layers.advanced_activations.ELU()(conv9)
    conv9 = Conv2D(32, 3, activation='relu',padding='same')(conv9)
    crop9 = Cropping2D(cropping=((16, 16), (16, 16)))(conv9)
    conv9 = BatchNormalization(axis=-1)(crop9)
    conv9 = keras.layers.advanced_activations.ELU()(conv9)
    #conv10 = Convolution2D(n_label, 1, 1, activation='sigmoid')(conv9)
    conv10 = Conv2D(n_label, 1, activation='softmax')(conv9)
    model = Model(input=inputs, output=conv10)
    return model