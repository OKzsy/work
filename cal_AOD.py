import math

a = -(math.log(0.2695 / 0.7349) / math.log(869.9 / 439.4))
b = 0.2695 / 869.9 ** (-a)


tao = b * 550 ** (-a)

print(tao)

tao2 = (550 / 439.4) ** (-1.466228) * 0.734949

print(tao2)

