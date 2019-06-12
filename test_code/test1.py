import numpy as np
import numexpr as ne

arr = np.array([-1, 2, 3, np.nan])
bar = np.array([-1, 5, 3, np.nan])
phi = 1
# index = np.where(np.isnan(arr))
var = ne.evaluate("(bar - phi) ** 2")
print(var)
