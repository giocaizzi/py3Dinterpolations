"""model wrapper for interpolation"""

import numpy as np

from ..core.griddata import GridData
from ..core.grid3d import Grid3D
from .models import ModelWrapper


class Modeler:
    """modeler class for 3d modelling

    This class applies a model defined within the ModelWrapper
    class to a Grid3D instance

    Currently supports:
        Statistical:
            - Ordinary Kriging : `ordinary_kriging` (pykrige)
        Deterministic:
            - Inverse Distance Weighting : `idw`

    Args:
        griddata (GridData): GridData istance
        grid3d (Grid3D): Grid3D istance
        model_name (str): model name, default `ordinary_kriging`
        model_params (dict): model parameters

    Attributes:
        griddata (GridData): GridData istance
        grid3d (Grid3D): Grid3D istance
        model (object): model object
        results (dict): dictionary with interpolated and variance grids

    Examples:
        >>> # modeler
        >>> modeler = Modeler(griddata, grid3d)
        >>> # predict
        >>> interpolated = modeler.predict()

    """

    model: ModelWrapper
    results: dict

    def __init__(
        self,
        griddata: GridData,
        grid3d: Grid3D,
        model_name: str = "ordinary_kriging",
        model_params: dict = {},
    ):
        # griddata and grid3d
        self._griddata = griddata
        self._grid3d = grid3d
        self._model_name = model_name
        self._model_params = model_params

        # model
        self.model = ModelWrapper(
            model_name,
            self.griddata.numpy_data[:, 0:3],  # X
            self.griddata.numpy_data[:, 3],  # value Y
            **model_params,
        )

    @property
    def griddata(self) -> GridData:
        return self._griddata

    @property
    def grid3d(self) -> Grid3D:
        return self._grid3d

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_params(self) -> dict:
        return self._model_params

    def predict(self, **kwargs) -> np.ndarray:
        """makes predictions considering all past preprocessing

        - if normalization was applied, predict on normalized grid
        - if standardized data, reverse standardization
        - reshape from zxy to xyz (pykrige output)

        Args:
            grids_arrays (dict): dictionary with x, y, z grids 1d np.ndarray

        Returns:
            interpolated (np.ndarray): interpolated grid
        """
        # make predictions on normalized grid if normalization was applied
        # "GRID" prediction
        if "normalization" in self.griddata.preprocessor_params.keys():
            grids_arrays = self.grid3d.normalized_grid
        else:
            grids_arrays = self.grid3d.grid

        # point prediction
        if "normalization" in self.griddata.preprocessor_params.keys():
            mesh = self.grid3d.normalized_mesh
        else:
            mesh = self.grid3d.mesh

        # harcdcoded for skleran
        prediction_points = np.concatenate(
        (
            mesh["X"].reshape(-1,1),
            mesh["Y"].reshape(-1,1),
            mesh["Z"].reshape(-1,1)
        ),axis=1
        )

        # predict values
        # pykrige ordinarykrigin3d class returns a tuple
        # X : N, Y : M, Z : L
        # shape (L, M, N)
        interpolated = self.model.predict(
            prediction_points,
            **kwargs,
        )
        # probability
        if hasattr(self.model.model,"predict_proba"):
            probabiliy = self.model.model.predict_proba(
                prediction_points,
                **kwargs,
            )
            # some classificators returns array
            probabiliy = probabiliy.max(axis=1)

        else:
            probabiliy = None

        # variance
        variance = None

        # if standardized data, reverse standardization
        if "standardization" in self.griddata.preprocessor_params:
            interpolated = _reverse_standardized(
                interpolated, self.griddata.preprocessor_params["standardization"]
            )
        # save results
        self.results = {
            "interpolated": interpolated.reshape(self.grid3d.mesh["X"].shape), # hardcoding point calculation
            "probability":probabiliy.reshape(self.grid3d.mesh["X"].shape), # hardcoding
            "variance": variance,
        }

        # sets results  also in associated grid3d
        self.grid3d.results = self.results

        # return interpolated grid
        return interpolated


def _reverse_standardized(data: np.ndarray, standardization: dict) -> np.ndarray:
    """reverse standardization of a 1d numpy array

    considers that data could be none, in which case returns an empty array
    """
    return data * standardization["std"] + standardization["mean"]
