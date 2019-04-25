# -*- coding: utf-8 -*-
"""
Created on Wed Jun  6 14:41:04 2018

@author: 01
"""

import time
import os
import numpy as np
import pandas as pd

import keras
from keras import layers
from keras.models import Sequential
from keras.utils import np_utils
from keras.callbacks import ModelCheckpoint
from keras import optimizers


from tensorflow.contrib.keras.api.keras.utils import plot_model
from sklearn.model_selection import StratifiedShuffleSplit
from keras.utils.training_utils import multi_gpu_model
from sklearn.model_selection import StratifiedShuffleSplit
import tensorflow as tf
from tensorflow.python.client import device_lib
from keras import backend as K
import matplotlib as mplot
mplot.use('Agg')
import matplotlib.pyplot as plt




config = tf.ConfigProto(log_device_placement=True ) 
config.gpu_options.allow_growth = True
sess = tf.Session(config = config) 
K.set_session(sess)



patch_size = 7
channel =4
epochs = 30
b_size = 256
LR = 0.003
n=4



def read_csv(in_file):
    csv_shape =  pd.read_csv(in_file, header = None, nrows = 1).shape
    out_data = np.zeros((csv_shape[0], csv_shape[1]), dtype=np.float)
    chunksize = 10 ** 6
    for chunk in pd.read_csv(in_file, header = None, chunksize=chunksize):
        out_data = np.vstack((out_data, chunk.values))
        chunk = None

    return out_data[1:, :]


def get_available_gpus():
    """
    code from http://stackoverflow.com/questions/38559755/how-to-get-current-available-gpus-in-tensorflow
    """
    from tensorflow.python.client import device_lib as _device_lib
    local_device_protos = _device_lib.list_local_devices()

    return [x.name for x in local_device_protos if x.device_type == 'GPU']

###载入数据
def load_data(in_file):
    print(in_file)
    data = read_csv(in_file)
    x=data[:,0:-1]/10000#数据
    y=data[:,-1]#标签
    return x,y


#########模型结构
def build_model(patch_size=7,channel=4):
    with tf.device("/cpu:0"):
        model = Sequential()
        model.add(layers.Conv2D(100, (2, 2), activation='relu', input_shape=(patch_size,patch_size,channel),padding='same'))
        model.add(layers.MaxPooling2D((2, 2)))
        model.add(layers.Conv2D(100, (2, 2), activation='relu',padding='same'))
        model.add(layers.MaxPooling2D((2, 2)))
        model.add(layers.Conv2D(100, (1, 1), activation='relu',padding='same'))
        model.add(layers.Flatten())
        #model.add(layers.Dropout(rate=0.05))
        model.add(layers.Dense(200, activation='relu', kernel_initializer=keras.initializers.glorot_normal(seed=None)))
        model.add(layers.Dense(n,activation='softmax'))
    parallel_model = multi_gpu_model(model, 2)
    return model, parallel_model


def plot_loss(history,model_outpath):
    #画出损失图
    loss = history.history['loss']
    val_loss = history.history['val_loss']
    epochs = range(1, len(loss) + 1)
    plt.plot(epochs, loss, 'bo', label='Training loss')
    plt.plot(epochs, val_loss, 'b', label='Validation loss')
    plt.legend()
    plt.title('Training and validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.savefig(model_outpath +"//"+ 'loss.png')
    plt.close()
    return 0

def plot_acc(history,model_outpath):
    #画出准确率图
    acc = history.history['acc']
    val_acc = history.history['val_acc']
    epochs = range(1, len(acc) + 1)
    plt.plot(epochs, acc, 'bo', label='Training acc')
    plt.plot(epochs, val_acc, 'b', label='Validation acc')
    plt.legend()
    plt.title('Training and validation accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Acc')
    plt.savefig(model_outpath +"//"+ 'acc.png')
    plt.close()
    return 0

########
class ParallelModelCheckpoint(ModelCheckpoint):
	def __init__(self,model,filepath, monitor='val_loss', verbose=1,
		save_best_only=True,
		mode='min'):
		self.single_model = model
		super(ParallelModelCheckpoint,self).__init__(filepath, monitor, verbose,save_best_only, mode )

	def set_model(self, model):
		super(ParallelModelCheckpoint,self).set_model(self.single_model)
#######




#######main function#####################
def main(data_path,model_outpath,my_log_dir):
    in_file1 = data_path + 'train.csv'
    in_file2 = data_path + 'test.csv'
    x_train,y_train = load_data(in_file1)
    x_val,y_val = load_data(in_file2)

    y_train=np_utils.to_categorical(y_train)
    y_val=np_utils.to_categorical(y_val)

    x_train=x_train.reshape(x_train.shape[0],patch_size,patch_size,channel)
    x_val=x_val.reshape(x_val.shape[0],patch_size,patch_size,channel)

    model, parallel_model = build_model()
    ops = keras.optimizers.Adam(lr=LR)
    parallel_model.compile(optimizer=ops, loss='categorical_crossentropy', metrics=['accuracy'])

#####callbacks
    filepath=os.path.join(model_outpath,'model-ep{epoch:03d}-loss{loss:.3f}-val_loss{val_loss:.3f}-acc{acc:.3f}-val_cc{val_acc:.3f}.h5')

    checkpoint = ParallelModelCheckpoint(model,filepath)
    reduceLR = keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1,mode='min',verbose=1)
    early_stopping = keras.callbacks.EarlyStopping(monitor='acc', patience=5)
    tensorboard = keras.callbacks.TensorBoard(log_dir=my_log_dir,histogram_freq=0,embeddings_freq=0)

    datagen = keras.preprocessing.image.ImageDataGenerator(rotation_range=0, horizontal_flip=False)
    history = parallel_model.fit_generator(datagen.flow(x_train, y_train, batch_size=b_size),
                                           steps_per_epoch=x_train.shape[0] / b_size,
                                           validation_data=(x_val, y_val),
                                           epochs=epochs,
                                           use_multiprocessing=True,
                                           workers=30,
                                           verbose=1,
                                           max_q_size=256,
                                           callbacks=[reduceLR, checkpoint, tensorboard, early_stopping])
#history =parallel_model.fit(x_train,y_train,batch_size=b_size,epochs=epochs,callbacks=callbacks_list,validation_data=(x_val,y_val))

    df_history=pd.DataFrame(history.history)
    df_history.to_csv(os.path.join(model_outpath,"history.csv"))

    plot_loss(history,model_outpath)
    plt.clf()
    plot_acc(history,model_outpath)

    model.save(os.path.join(model_outpath,'cnn1_patch_model.h5'))
    model.save_weights(os.path.join(model_outpath,'cnn1_patch_model_weights.h5'))

if __name__ == '__main__':
    start = time.time()
    data_path = "/mnt/glusterfs/zhengyang_dengzhou_xiaomai/zhengyang/5751/csv_origin/"
    model_outpath = r"/mnt/glusterfs/zhengyang_dengzhou_xiaomai/zhengyang/5751/model_origin/0.003_256"
    my_log_dir = "/mnt/glusterfs/zhengyang_dengzhou_xiaomai/zhengyang/5751/model_origin/my_log"

    for path in model_outpath,my_log_dir:
        if os.path.exists(path) == False:
            os.makedirs(path)
    main(data_path,model_outpath,my_log_dir)
    end = time.time()
    print("time: %.2f min." % ((end - start) / 60))