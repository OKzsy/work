#!/usr/bin/env python
# -*- coding:utf-8 -*-

class Car():
    """一次模拟汽车的简单尝试"""

    def __init__(self, make, model, year):
        self.make = make
        self.model = model
        self.year = year
        self.year = year
        self.odometer_reading = 0

    def get_descriptive_name(self):
        long_name = str(self.year) + ' ' + self.make + ' ' + self.model
        return long_name.title()

    def read_odometer(self):
        print("This car has " + str(self.odometer_reading) + " miles on it.")

    def update_odometer(self, mileage):
        if mileage >= self.odometer_reading:
            self.odometer_reading = mileage
        else:
            print("You can't roll back an odometer")

    def increment_odometer(self, miles):
        self.odometer_reading += miles


class ElectricCar(Car):
    """电动车的独特之处"""

    def __init__(self, make, model, year,battery_size):
        """初始化父类的属性"""
        super().__init__(make, model, year)
        self.battery_size=battery_size

    def describe_battery(self):
        print("This car has a "+str(self.battery_size)+"-KWh battery.")


my_tesla = ElectricCar('tesla', 'models', 2016,70)
my_tesla.update_odometer(100)
my_tesla.read_odometer()
