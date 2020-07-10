import io, os, sys, types, importlib, re
from IPython import get_ipython
from nbformat import read
from IPython.core.interactiveshell import InteractiveShell
from pathlib import Path

print(str(Path(__file__).parent))
defaultFolder = str(Path(__file__).parent)

def find_notebook(fullname, path=[defaultFolder]):
        """find a notebook, given its fully qualified name and an optional path

        This turns "foo.bar" into "foo/bar.ipynb"
        and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
        does not exist.
        """

        name =  fullname.rsplit('.', 1)[-1]
        print("after split: " + name)
        if not path:
            path = ['']
        print("path: ")
        print(path)
        for d in path:
            fld = os.path.join(d, name)
            if os.path.isdir(fld):
                print("foldertest: " + fld)
                return fld
            nb_path = os.path.join(d, name + ".ipynb")
            print(nb_path)
            if os.path.isfile(nb_path):
                return nb_path
            # let import Notebook_Name find "Notebook Name.ipynb"
            nb_path = nb_path.replace("_", " ")
            if os.path.isfile(nb_path):
                return nb_path
class NotebookLoader(object):
    """Module Loader for Jupyter Notebooks"""
    def __init__(self, path=defaultFolder):
        self.shell = InteractiveShell.instance()
        self.path = path

    def load_module(self, fullname):
        """import a notebook as a module"""
        path = find_notebook(fullname, self.path)

        print ("importing Jupyter notebook from %s" % path)

        # load the notebook object
        with io.open(path, 'r', encoding='utf-8') as f:
            nb = read(f, 4)


        # create the module and add it to sys.modules
        # if name in sys.modules:
        #    return sys.modules[name]
        mod = types.ModuleType(fullname)
        mod.__file__ = path
        mod.__loader__ = self
        mod.__dict__['get_ipython'] = get_ipython
        sys.modules[fullname] = mod

        # extra work to ensure that magics that would affect the user_ns
        # actually affect the notebook module's ns
        save_user_ns = self.shell.user_ns
        self.shell.user_ns = mod.__dict__

        try:
          for cell in nb.cells:
            if cell.cell_type == 'code':
                # transform the input to executable Python
                code = self.shell.input_transformer_manager.transform_cell(cell.source)
                # run the code in themodule
                exec(code, mod.__dict__)
        finally:
            self.shell.user_ns = save_user_ns
        return mod

class NotebookFinder(object):
    """Module finder that locates Jupyter Notebooks"""
    def __init__(self):
        self.loaders = {}

    def find_module(self, fullname, path=[defaultFolder]):

        print(fullname)
        print(path)
        if not path:
            path = [defaultFolder]
        nb_path = find_notebook(fullname, path)
        if not nb_path:
            return

        key = nb_path

        if key not in self.loaders:
            self.loaders[key] = NotebookLoader(path)

        return self.loaders[key]
        
if "JUPLOADER" not in os.environ:
    sys.path.append(defaultFolder)

    print("Appending finder")
    os.environ["JUPLOADER"] = "1"

    sys.meta_path.append(NotebookFinder())

