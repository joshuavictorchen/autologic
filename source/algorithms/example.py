from algorithms import HeatGenerator, register


@register
class AnExampleAlgorithm(HeatGenerator):

    def generate(self, event):
        """
        This is an example algorithm. It does nothing and is just a scaffold as an example.

        It is automatically made available as a CLI option since it is decorated with the @register function.

        Algorithms receive a pre-instantiated `Event` and are expected to assign `Categories` to `Heats`,
        and assign roles to all `Participants` by mutating the `Event`.
        """

        print("\n  ---------------------------")
        print(f"  >>> your algorithm here <<<")
        print("  ---------------------------")
