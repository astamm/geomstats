"""Decorator to handle vectorization.

This abstracts the backend type.
This assumes that functions are implemented to return vectorized outputs.
"""

import geomstats.backend as gs

POINT_TYPES_TO_NDIMS = {
    'scalar': 2,
    'vector': 2,
    'matrix': 3}


def squeeze_output_dim_0(initial_shapes, point_types):
    """Determine if the output needs to be squeezed on dim 0.

    The dimension 0 is squeezed iff all input parameters:
    - contain one sample,
    - have the corresponding dimension 0 squeezed,
    i.e. if all input parameters have ndim strictly less than the ndim
    corresponding to their vectorized shape.

    Parameters
    ----------
    initial_ndims : list
        Initial ndims of input parameters, as entered by the user.
    point_types : list
        Associated list of point_type of input parameters.

    Returns
    -------
    squeeze : bool
        Boolean deciding whether to squeeze dim 0 of the output.
    """
    for in_shape, point_type in zip(initial_shapes, point_types):
        in_ndim = None
        if in_shape is not None:
            in_ndim = len(in_shape)
        if point_type != 'else' and in_ndim is not None:
            vect_ndim = POINT_TYPES_TO_NDIMS[point_type]
            assert in_ndim <= vect_ndim
            if in_ndim == vect_ndim:
                return False
    return True


def is_scalar(vect_array):
    """Test if an array represents a scalar."""
    has_ndim_2 = vect_array.ndim == 2
    if not has_ndim_2:
        return False
    has_singleton_dim_1 = vect_array.shape[1] == 1
    return has_singleton_dim_1


def squeeze_output_dim_1(result, initial_shapes, point_types):
    """Determine if the output needs to be squeezed on dim 1.

    This happens if the user represents scalars as array of shapes:
    [n_samples,] instead of [n_samples, 1]
    Dimension 1 is squeezed by default if point_type is 'scalar'.
    Dimension 1 is not squeezed if the user inputs at least one scalar with
    a singleton in dimension 1.

    Parameters
    ----------
    result: array-like
        Result output by the function, before reshaping.
    initial_shapes : list
        Initial shapes of input parameters, as entered by the user.
    point_types : list
        Associated list of point_type of input parameters.

    Returns
    -------
    squeeze : bool
        Boolean deciding whether to squeeze dim 1 of the output.
    """
    if not is_scalar(result):
        return False

    for shape, point_type in zip(initial_shapes, point_types):
        if point_type != 'else' and shape is not None:
            ndim = len(shape)
            if point_type == 'scalar':
                assert ndim <= 2
                if ndim == 2:
                    return False
    return True


def decorator(point_types):
    """Vectorize geomstats functions.

    This decorator assumes that its function:
    - works with fully-vectorized inputs,
    - returns fully-vectorized outputs,

    where "fully-vectorized" means that:
    - one scalar has shape [1, 1],
    - n scalars have shape [n, 1],
    - one d-D vector has shape [1, d],
    - n d-D vectors have shape [n, d],
    etc.

    The decorator:
    - converts the inputs into fully-vectorized inputs,
    - calls the function,
    - adapts the output shapes to match the users' expectations.

    Parameters
    ----------
    point_types : list
        List of inputs' point_types, including for optional inputs.
        The `point_type`s of optional inputs will not be read
        by the decorator if the corresponding input is not given.
    """
    if not isinstance(point_types, list):
        point_types = list(point_types)

    def aux_decorator(function):
        def wrapper(*args, **kwargs):
            args_point_types = point_types[:len(args)]
            kwargs_point_types = point_types[len(args):]

            in_shapes = args_initial_shapes(
                args_point_types, args)
            kw_in_shapes = kwargs_initial_shapes(
                kwargs_point_types, kwargs)

            in_shapes.extend(kw_in_shapes)

            vect_args = vectorize_args(args_point_types, args)
            vect_kwargs = vectorize_kwargs(kwargs_point_types, kwargs)

            result = function(*vect_args, **vect_kwargs)

            if squeeze_output_dim_1(result, in_shapes, point_types):
                if result.shape[1] == 1:
                    result = gs.squeeze(result, axis=1)

            if squeeze_output_dim_0(in_shapes, point_types):
                if result.shape[0] == 1:
                    result = gs.squeeze(result, axis=0)
            return result
        return wrapper
    return aux_decorator


def args_initial_shapes(point_types, args):
    """Extract shapes and ndims of input args.

    Return a lists that stores the shapes of the input args.
    """
    initial_shapes = []

    for i_arg, arg in enumerate(args):
        point_type = point_types[i_arg]

        if point_type == 'scalar':
            arg = gs.array(arg)

        if point_type == 'else' or arg is None:
            initial_shapes.append(None)
        else:
            initial_shapes.append(gs.shape(arg))
    return initial_shapes


def kwargs_initial_shapes(point_types, kwargs):
    """Extract shapes and ndims of input kwargs."""
    initial_shapes = []

    for i_arg, arg in enumerate(kwargs.values()):
        point_type = point_types[i_arg]

        if point_type == 'scalar':
            arg = gs.array(arg)

        if point_type == 'else' or arg is None:
            initial_shapes.append(None)
        else:
            initial_shapes.append(gs.shape(arg))
    return initial_shapes


def vectorize_args(point_types, args):
    """Vectorize input args."""
    vect_args = []
    for i_arg, arg in enumerate(args):
        point_type = point_types[i_arg]
        if point_type == 'else' or arg is None:
            vect_arg = arg
        elif point_type == 'scalar':
            vect_arg = gs.to_ndarray(arg, to_ndim=1)
            vect_arg = gs.to_ndarray(vect_arg, to_ndim=2, axis=1)
        elif point_type in ['vector', 'matrix']:
            vect_arg = gs.to_ndarray(
                arg, to_ndim=POINT_TYPES_TO_NDIMS[point_type])
        vect_args.append(vect_arg)
    return tuple(vect_args)


def vectorize_kwargs(point_types, kwargs):
    """Vectorize input kwargs."""
    vect_kwargs = {}
    for i_arg, key_arg in enumerate(kwargs.keys()):
        point_type = point_types[i_arg]
        arg = kwargs[key_arg]
        if point_type == 'else' or arg is None:
            vect_arg = arg
        elif point_type == 'scalar':
            vect_arg = gs.to_ndarray(arg, to_ndim=1)
            vect_arg = gs.to_ndarray(vect_arg, to_ndim=2, axis=1)
        elif point_type in ['vector', 'matrix']:
            vect_arg = gs.to_ndarray(
                arg, to_ndim=POINT_TYPES_TO_NDIMS[point_type])
        vect_kwargs[key_arg] = vect_arg
    return vect_kwargs
