import math
import numpy as np
import matplotlib.pyplot as plt

from osgeo import gdal
from train import get_model, normalize, n_classes, tif_read
from keras.models import load_model
from keras.preprocessing.image import img_to_array


def nor(x):
    x = x / 10000.0
    return x


def tif_read(in_file):
    data_ds = gdal.Open(in_file)
    data = data_ds.ReadAsArray()
    return data


def write_geotiff(fname, data, cols, rows, geo_transform, projection):
    """Create a GeoTIFF file with the given data."""
    # print(data.shape)
    driver = gdal.GetDriverByName('GTiff')

    dataset = driver.Create(fname, cols, rows, 1, gdal.GDT_Byte)
    dataset.SetGeoTransform(geo_transform)
    dataset.SetProjection(projection)
    band = dataset.GetRasterBand(1)
    band.WriteArray(data)
    dataset = None


def predict(x, model, patch_size, n_classes=n_classes):
    npatches_vertical = math.ceil(x.shape[0] / patch_size)
    npatches_horizontal = math.ceil(x.shape[1] / patch_size)
    extended_height = patch_size * npatches_vertical
    extended_width = patch_size * npatches_horizontal
    ext_x = np.zeros(shape=(extended_height, extended_width, x.shape[2]), dtype=np.float32)
    ext_x[:x.shape[0], :x.shape[1], :] = x
    img_zeros = np.zeros((ext_x.shape[0], ext_x.shape[1]))
    # img_zeros = np.zeros((x.shape[0], x.shape[1]))
    for i in range(int(ext_x.shape[0] / patch_size) - 1):
        for j in range(int(ext_x.shape[1] / patch_size) - 1):
            img_pred = model.predict(np.expand_dims(ext_x[patch_size * i:patch_size * (i + 1) + patch_size,
                                                    patch_size * j:patch_size * (j + 1) + patch_size, :], 0))
            img_pred = np.squeeze(img_pred)
            img_zeros[patch_size * i:patch_size * (i + 1) + patch_size,
            patch_size * j:patch_size * (j + 1) + patch_size] = img_pred.argmax(axis=2)
    return img_zeros[:x.shape[0], :x.shape[1]]


def make_prediction_cropped(X_train, model, initial_size=(128, 128), final_size=(96, 96), num_channels=4, num_masks=2):
    shift = int((initial_size[0] - final_size[0]) / 2)
    X_train = X_train.transpose(2, 0, 1)
    height = X_train.shape[1]
    width = X_train.shape[2]

    if height % final_size[1] == 0:
        num_h_tiles = int(height / final_size[1])
    else:
        num_h_tiles = int(height / final_size[1]) + 1

    if width % final_size[1] == 0:
        num_w_tiles = int(width / final_size[1])
    else:
        num_w_tiles = int(width / final_size[1]) + 1

    rounded_height = num_h_tiles * final_size[0]
    rounded_width = num_w_tiles * final_size[0]

    padded_height = rounded_height + 2 * shift
    padded_width = rounded_width + 2 * shift

    padded = np.zeros((num_channels, padded_height, padded_width))

    padded[:, shift:shift + height, shift: shift + width] = X_train

    # add mirror reflections to the padded areas
    up = padded[:, shift:2 * shift, shift:-shift][:, ::-1]
    padded[:, :shift, shift:-shift] = up

    lag = padded.shape[1] - height - shift
    bottom = padded[:, height + shift - lag:shift + height, shift:-shift][:, ::-1]
    padded[:, height + shift:, shift:-shift] = bottom

    left = padded[:, :, shift:2 * shift][:, :, ::-1]
    padded[:, :, :shift] = left

    lag = padded.shape[2] - width - shift
    right = padded[:, :, width + shift - lag:shift + width][:, :, ::-1]
    padded[:, :, width + shift:] = right

    h_start = range(0, padded_height, final_size[0])[:-1]
    assert len(h_start) == num_h_tiles

    w_start = range(0, padded_width, final_size[0])[:-1]
    assert len(w_start) == num_w_tiles

    temp = []
    for h in h_start:
        for w in w_start:
            temp += [padded[:, h:h + initial_size[0], w:w + initial_size[0]]]
    temp = np.array(temp).transpose([0, 2, 3, 1])
    prediction = model.predict(temp)
    prediction = np.squeeze(prediction)
    prediction = prediction.argmax(axis=-1)
    predicted_mask = np.zeros((rounded_height, rounded_width))

    for j_h, h in enumerate(h_start):
        for j_w, w in enumerate(w_start):
            i = len(w_start) * j_h + j_w
            predicted_mask[h: h + final_size[0], w: w + final_size[0]] = prediction[i]

    return predicted_mask[:height, :width]


def get_geo(infile):
    ds = gdal.Open(infile)
    geo = ds.GetGeoTransform()
    proj = ds.GetProjection()
    cols = ds.RasterXSize  # 列
    rows = ds.RasterYSize  # 行
    return geo, proj, cols, rows


if __name__ == '__main__':
    patch_size = 64
    modelfile = r"/home/zhaoshaoshuai/test_data/unet_test/unet_best_model.h5"
    model = load_model(modelfile)
    test_id = '08'
    filepath1 = r"/home/zhaoshaoshuai/test_data/unet_test/"
    img = nor(tif_read(filepath1 + '{}.tif'.format(test_id)).transpose([1, 2, 0]))  # make channels last
    geo, proj, cols, rows = get_geo(filepath1 + '{}.tif'.format(test_id))

    # pre = predict(img, model, patch_size=patch_size, n_classes=n_classes)  # make channels first
    pre = make_prediction_cropped(img, model, initial_size=(128, 128),
                                  final_size=(96, 96),
                                  num_masks=n_classes,
                                  num_channels=4)

    write_geotiff('/home/luote/project/zhiyan/GF1648830_jaccard_c.tif', pre, cols, rows, geo, proj)
