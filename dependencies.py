import os


class Dependencies:
    def check(self, output):
        print("")
        output.print_step_title("Checking dependencies")
        if "BOOST_ROOT" not in os.environ:
            raise RuntimeError("Missing dependency: BOOST_ROOT environment"
                               " variable not set")
        else:
            print("    BOOST_ROOT: " + os.environ["BOOST_ROOT"])
        output.next_step()
