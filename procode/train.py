#coding=utf-8
# from unetmodel import *
from gen_patches import *
# from unet import *
from unetmodel import *
from keras.callbacks import CSVLogger
from keras.callbacks import TensorBoard
from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
import os.path
import keras
import tensorflow as tf

import numpy as np
from keras.utils import np_utils
try:
    from osgeo import gdal
except ImportError:
    import gdal

config = tf.ConfigProto()
# config.gpu_options.allow_growth = True
config.gpu_options.per_process_gpu_memory_fraction = 0.8
sess = tf.Session(config=config)
K.set_session(sess)


n_channels = 4
n_classes = 2
epoch = 100
patch_size = 128
batch_size = 64
train_size = 128
val_size = 16


class ParallelModelCheckpoint(ModelCheckpoint):
    def __init__(self,model,filepath, monitor='val_loss', verbose=1,
        save_best_only=True,
        mode='min'):
        self.single_model = model
        super(ParallelModelCheckpoint,self).__init__(filepath, monitor, verbose,save_best_only, mode )

    def set_model(self, model):
        super(ParallelModelCheckpoint,self).set_model(self.single_model)




def get_model():
    return unet(n_classes,patch_size,n_channels)

def normalize(img):
    min = img.min()
    max = img.max()
    x = 2.0 * (img - min) / (max - min) - 1.0
    return x

def nor(x):
    x = x/10000.0
    return x
#tif读取
def tif_read(in_file):
    data_ds = gdal.Open(in_file)
    data = data_ds.ReadAsArray()
    return data


trainIds = [str(i).zfill(2) for i in range(0, 8)]


if __name__ == '__main__':
    X_DICT_TRAIN = dict()
    Y_DICT_TRAIN = dict()
    X_DICT_VALIDATION = dict()
    Y_DICT_VALIDATION = dict()
    print('Reading images')

    model_outpath = r"/home/luote/project/zhiyan/model/"

    for img_id in trainIds:
        im = nor(tif_read(r"/home/luote/project/zhiyan/data/src/{}.tif".format(img_id)).transpose(1,2,0))
        mask = tif_read(r"/home/luote/project/zhiyan/data/label/{}.tif".format(img_id))
        mask[mask==255]=1
        mask = np_utils.to_categorical(mask)
        train_xsz = int(3 / 4 * im.shape[0])  # use 75% of image as train and 25% for validation
        X_DICT_TRAIN[img_id] = im[:train_xsz, :, :]
        Y_DICT_TRAIN[img_id] = mask[:train_xsz, :,:]
        X_DICT_VALIDATION[img_id] = im[train_xsz:, :, :]
        Y_DICT_VALIDATION[img_id] = mask[train_xsz:, :,:]
        print(img_id + ' read')
    print('Images were read')

    def train_net():
        print("start train net")
        x_train, y_train = get_patches(X_DICT_TRAIN, Y_DICT_TRAIN, n_patches=train_size, sz=patch_size)
        y_train = y_train[:, 16:16 + patch_size - 32, 16:16 + patch_size - 32, :]
        x_val, y_val = get_patches(X_DICT_VALIDATION, Y_DICT_VALIDATION, n_patches=val_size, sz=patch_size)
        y_val = y_val[:, 16:16 + patch_size - 32, 16:16 + patch_size - 32,:]
        #q = len(X_DICT_TRAIN)
        with tf.device('/cpu:0'):
            model = get_model()

        from keras.utils import multi_gpu_model

        parallel_model = multi_gpu_model(model, gpus=2)
        # categorical_crossentropy对应softmax，应用于多分类。binary_crossentropy用于一分类。
        #parallel_model.compile(optimizer=Adam(lr=0.0001), loss='categorical_crossentropy', metrics=['accuracy'])
        #parallel_model.compile(optimizer=Adam(lr=0.0001), loss='binary_crossentropy', metrics=['accuracy'])
        parallel_model.compile(optimizer=Adam(lr=0.0001), loss=jaccard_coef_loss, metrics=['binary_crossentropy', jaccard_coef_int])

        save_path = os.path.join(model_outpath +
                                'model-ep{epoch:03d}-loss{loss:.3f}-val_loss{val_loss:.3f}-acc{acc:.3f}-val_cc{val_acc:.3f}.h5')

        model_checkpoint = ParallelModelCheckpoint(model,save_path, monitor='val_loss', save_best_only=True)
        reduceLR = keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, mode='auto', verbose=0)
        callable = [reduceLR]
        parallel_model.fit(x_train, y_train, batch_size=batch_size, epochs=epoch,
                  verbose=2, shuffle=True,
                  callbacks=callable,
                  validation_data=(x_val, y_val))
        model.save(model_outpath+ 'unet_best_model.h5')
        return model


    train_net()