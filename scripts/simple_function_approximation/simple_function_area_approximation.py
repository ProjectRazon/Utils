import numpy as np
from manim import *
import matplotlib.cm as cm
import matplotlib.colors as mcolors

config.background_color = "#000000"
TEXT_COLOR = WHITE
FUNCTION_COLOR = ORANGE

class SimpleFunctionApproximation(Scene):
    """
    An animation demonstrating the approximation of a non-negative
    real function by a series of rectangles.
    
    This version features a custom "splitting" animation for a highly
    intuitive visualization of the refinement process.
    """
    def construct(self):
        # 1. --- SCENE SETUP ---
        axes = Axes(
            x_range=[-8.5, 8.5, 2],
            y_range=[0, 4, 1],
            x_length=12,
            y_length=6,
            axis_config={"color": GRAY_A},
            x_axis_config={"numbers_to_include": np.arange(-8, 9, 2)},
            y_axis_config={"numbers_to_include": np.arange(0, 5, 1)},
        )
        axis_labels = axes.get_axis_labels(x_label="x", y_label="y = f(x)")

        def func_to_approximate(x):
            # A cubic function that stays mostly within the y-range [0, 3.5]
            return 3 / 256 * np.power(x, 3) - 9 / 16 * x + 1.75
        
        # Max value the function attains in the domain for coloring purposes
        func_max_val = 3.5

        graph = axes.plot(
            func_to_approximate,
            color=FUNCTION_COLOR,
            x_range=[-8, 8],
            stroke_width=5
        )
        graph_label = axes.get_graph_label(graph, label="f(x)", x_val=-4.5, direction=UP)

        self.add(axes, axis_labels, graph, graph_label)
        self.wait(1)

        # 2. --- RECTANGLE CREATION LOGIC ---
        def create_simple_function_rectangles(n, x_domain=[-8, 8], dx=0.001):
            """Creates a VGroup of rectangles approximating the function for a given n."""
            simple_func = lambda x: np.floor(func_to_approximate(x) * n) / n
            rectangles = VGroup()
            x_values = np.arange(x_domain[0], x_domain[1] + dx, dx)
            
            colormap = cm.viridis_r
            norm = mcolors.Normalize(vmin=0, vmax=func_max_val)
            
            current_y = simple_func(x_values[0])
            segment_start_x = x_values[0]

            for x_val in x_values[1:]:
                new_y = simple_func(x_val)
                if not np.isclose(new_y, current_y):
                    if current_y > 1e-6:
                        rect_width = x_val - segment_start_x
                        rect = Rectangle(
                            width=axes.x_axis.unit_size * rect_width,
                            height=axes.y_axis.unit_size * current_y,
                            stroke_width=0,
                            fill_opacity=1,
                            color=mcolors.to_hex(colormap(norm(current_y)))
                        )
                        rect.move_to(axes.c2p(segment_start_x, 0), aligned_edge=DL)
                        rectangles.add(rect)
                    
                    segment_start_x = x_val
                    current_y = new_y
            
            if current_y > 1e-6:
                rect_width = x_values[-1] - segment_start_x
                rect = Rectangle(
                    width=axes.x_axis.unit_size * rect_width,
                    height=axes.y_axis.unit_size * current_y,
                    stroke_width=0,
                    fill_opacity=1,
                    color=mcolors.to_hex(colormap(norm(current_y)))
                )
                rect.move_to(axes.c2p(segment_start_x, 0), aligned_edge=DL)
                rectangles.add(rect)

            return rectangles

        # 3. --- ANIMATION ---
        n_values = [1, 2, 4, 8, 16, 32]
        
        # --- Create and display the initial state (n=1) ---
        current_n = n_values[0]
        current_approx_rects = create_simple_function_rectangles(current_n)
        

        self.play(
            FadeIn(current_approx_rects, shift=UP, lag_ratio=0.1)
        )
        self.wait(1.5)

        # --- Loop through n_values and create the custom splitting animation ---
        for i in range(1, len(n_values)):
            next_n = n_values[i]
            next_approx_rects = create_simple_function_rectangles(next_n)

            # --- CUSTOM SPLITTING ANIMATION LOGIC ---
            animations = []
            
            # Keep track of new rectangles that have a "parent"
            matched_new_rects = VGroup()

            # For each old rectangle, find the new ones that fall inside it
            for old_rect in current_approx_rects:
                children = VGroup()
                old_rect_x_center = old_rect.get_center()[0]
                old_rect_width = old_rect.width
                
                # Find all new rectangles whose center is within the old one's span
                for new_rect in next_approx_rects:
                    if abs(new_rect.get_center()[0] - old_rect_x_center) < old_rect_width / 2:
                        children.add(new_rect)
                
                if len(children) > 0:
                    # Create copies of the old rectangle to serve as the source of the transform
                    # This creates the visual effect of one object splitting into many
                    old_rect_copies = VGroup(*[old_rect.copy() for _ in children])
                    animations.append(ReplacementTransform(old_rect_copies, children))
                    matched_new_rects.add(*children)
                else:
                    # If an old rectangle has no children, it means the function
                    # value dropped, so it should disappear
                    animations.append(FadeOut(old_rect))

            # Any new rectangles that were not matched have no parent
            # (e.g., the function rose from zero). These should just fade in.
            unmatched_new_rects = VGroup(*[
                r for r in next_approx_rects if r not in matched_new_rects
            ])
            if len(unmatched_new_rects) > 0:
                animations.append(FadeIn(unmatched_new_rects))

            # Remove the original rectangles from the scene before playing the transforms
            self.remove(current_approx_rects)

            # Play the splitting animation and the label update together
            self.play(
                *animations,
                run_time=2.0
            )
            self.wait(1.5)
            
            current_approx_rects = next_approx_rects
            
        self.wait(3)