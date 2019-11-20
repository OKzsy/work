#!/usr/bin/env python
# -*- coding:utf-8 -*-

# python for make your own Neural Network
# code for a 3-layer neural network, and code for learning the MNIST
# dataset

import os
import sys
import time
import numpy as np
# scipy.special for the sigmoid function expit()
import scipy.special
# library for plotting arrays
import matplotlib.pyplot as plt


# neural network class definition
class neuralNetwork:

    # initialise the neural network
    def __init__(self, inputnodes, hiddennodes, outputnodes, learningrate):
        # set number of nodes in each input, hidden, output layer
        self.inodes = inputnodes
        self.hnodes = hiddennodes
        self.onodes = outputnodes
        # set learning rate
        self.lr = learningrate
        # link weight matrices, wih, who
        # weight inside the arrays are w_i_j, where link is from node
        # i to node j in the next layer
        # w11 w21
        # w12 w22 etc
        self.wih = np.random.normal(0.0, pow(self.hnodes, -0.5), (self.hnodes, self.inodes))
        self.who = np.random.normal(0.0, pow(self.onodes, -0.5), (self.onodes, self.hnodes))
        # activation function is the sigmoid function
        self.activation_function = lambda x: scipy.special.expit(x)
        pass

    # train the neural network
    def train(self, inputs_list, targets_list):
        # convert inputs list to 2d array
        inputs = np.array(inputs_list, ndmin=2).T
        targets = np.array(targets_list, ndmin=2).T

        # calculate signals into hidden layer
        hidden_inputs = np.dot(self.wih, inputs)
        # calculate the signals emerging from hidden layer
        hidden_outputs = self.activation_function(hidden_inputs)

        # calculate signals into final output layer
        final_inputs = np.dot(self.who, hidden_outputs)
        # calculate the signals emerging from final outputs layer
        final_outputs = self.activation_function(final_inputs)

        # error is the (target - actual)
        output_errors = targets - final_outputs
        # hidden layer error is the output_errors, split by weights,
        # recombined at hidden nodes
        hidden_errors = np.dot(self.who.T, output_errors)
        # update the weights for the links between the hidden and output
        # layers
        self.who += self.lr * np.dot((output_errors * final_outputs * (1.0 - final_outputs)),
                                     np.transpose(hidden_outputs))

        # update the weights for the links between the input and hidden layers
        self.wih += self.lr * np.dot((hidden_errors * hidden_outputs * (1.0 - hidden_outputs)),
                                     np.transpose(inputs))

        pass

    # query the neural network
    def query(self, inputs_list):
        # convert inputs list to 2d array
        inputs = inputs_list.T

        # calculate signals into hidden layer
        hidden_inputs = np.dot(self.wih, inputs)
        # calculate the signals emerging from hidden layer
        hidden_outputs = self.activation_function(hidden_inputs)

        # calculate signals into final output layer
        final_inputs = np.dot(self.who, hidden_outputs)
        # calculate the signals emerging from final output layer
        final_outputs = self.activation_function(final_inputs)

        return final_outputs


def main():
    # number of input, hidden and output nodes
    input_nodes = 784
    hidden_nodes = 300
    output_nodes = 10
    learning_rate = 0.1

    # create instance of neural network
    n = neuralNetwork(input_nodes, hidden_nodes, output_nodes, learning_rate)

    # define the train dataset file
    mnist_train_file = r"E:\MNIST_dataset\mnist_train.csv"
    # load the mnist training data CSV file into a list
    # training_data_file = open(mnist_train_file, 'r')
    # training_data_list = training_data_file.readlines()
    # training_data_file.close()
    training_data_array = np.loadtxt(mnist_train_file, delimiter=',').astype(np.int)

    # train the neural network

    # epochs is the number of times the training data set is used for training
    epochs = 7
    for e in range(epochs):
        # go through all records in the training data set
        for record in training_data_array:
            # split the record by the ',' commas
            # scale and shift the inputs
            inputs = (record[1:] / 255.0 * 0.99) + 0.01
            # create the target output values (all 0.01, except the desired label which is 0.99)
            targets = np.zeros(output_nodes) + 0.01
            # all_values[0] is the target label for this record
            targets[record[0]] = 0.99
            n.train(inputs, targets)
            pass

    # test the neural networl
    # load the mnist test data CSV file into a list
    mnist_test_file = r"E:\MNIST_dataset\mnist_test.csv"
    test_data_array = np.loadtxt(mnist_test_file, delimiter=',').astype(np.int)

    # # calculate the performance score, the fraction of correct answers
    accuracy_cnt = 0
    batch_size = 50
    for i in range(0, test_data_array.shape[0], batch_size):
        correct_label = test_data_array[i:i + batch_size, 0]
        inputs = test_data_array[i:i + batch_size, 1:] / 255.0 * 0.99 + 0.01
        outputs = n.query(inputs)
        label = np.argmax(outputs, axis=0)
        accuracy_cnt += np.sum(label == correct_label)
    print("performance = ", str(float(accuracy_cnt / test_data_array.shape[0])))


if __name__ == '__main__':
    start = time.time()
    main()
    end = time.time()
    print('time: {:^10.4f}'.format((end - start)))
