import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')

def f(x):
    """A polynomial function."""
    return x**3 - x**2 - 6*x

x = np.linspace(-3, 4, 500)
y = f(x)

fig, ax = plt.subplots(figsize=(10, 6))

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.spines['bottom'].set_position('zero')
ax.spines['left'].set_position('zero')

ax.plot(x, y, color='white', linewidth=2)

ax.fill_between(x, y, where=(y > 0), color='red', alpha=0.5, interpolate=True,
                label='Positive Area, f(x) > 0')
ax.fill_between(x, y, 0, where=(y < 0), color='blue', alpha=0.5, interpolate=True,
                label='Negative Area, f(x) < 0')

ax.legend()

plt.xticks([], [])
plt.yticks([], [])

plt.show()