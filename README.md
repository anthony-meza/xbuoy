# xbuoy

A package to aggregate buoy data (see [ndbc-api](https://github.com/CDJellen/ndbc-api)) into xarray objects so you can make cool plots like this!

<img width="585" alt="Screenshot 2024-10-16 at 5 13 39 PM" src="https://github.com/user-attachments/assets/9a64a9b2-21a4-48b6-8452-36e5807dcc2f">

## Installation

```bash
$ pip install --force-reinstall git+https://github.com/anthony-meza/xbuoy.git@main
```

or 


```bash
$ pip install --upgrade git+https://github.com/anthony-meza/xbuoy.git@main
```
## Usage

- TODO


## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`xbuoy` was created by Anthony Meza. It is licensed under the terms of the MIT license.

## Credits Development

`xbuoy` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).

Setting up came from the [`pypkg`](https://py-pkgs.org/03-how-to-package-a-python.html) instructions and poetry. 

If developing, use poetry. To initialize poetry, use `poetry install` in the root. Then add dependencies using `poetry add`. Finally, you can test build this using `poetry build`. Finally, the package can be installed into a conda enviornment using `pip install ./dist/xbuoy-X.X.X-py3-none-any.whl`
