import numpy as np
from suprb2.random_gen import Random
from suprb2.config import Config
from sklearn.metrics import *
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split


class Classifier:
    def __init__(self, lowers, uppers, local_model, degree):
        self.lowerBounds = lowers
        self.upperBounds = uppers
        self.model = local_model
        # TODO make this part of local model (as a class)
        self.degree = degree
        self.error = None
        # TODO expand this int into remember which was matched (to reduce
        # retraining when mutate didnt change the matched data)
        self.experience = None
        # if set this overrides local_model and outputs constant for all prediction requests
        self.constant = None

    def matches(self, X: np.array) -> np.array:
        l = np.reshape(np.tile(self.lowerBounds, X.shape[0]), (X.shape[0],
                                                               X.shape[1]))
        u = np.reshape(np.tile(self.upperBounds, X.shape[0]), (X.shape[0],
                                                               X.shape[1]))
        # Test if greater lower and smaller upper and return True for each line
        m = ((l < X) & (X < u)).all(1)
        return m

    def predict(self, X: np.ndarray) -> float:
        """
        Returns this classifier's prediction for the given input.
        """
        if X.ndim == 2:
            if self.constant is None:
                return self.model.predict(X)
            else:
                return np.repeat(self.constant, X.shape[0])
        else:
            if self.constant is None:
                # TODO why the last reshape?
                return self.model.predict(X.reshape((1, -1))).reshape(())
            else:
                return self.constant

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Fits this classifier to the given training data and computes its
        error on it using it's local model's score method.
        """
        self.constant = None
        if len(X) < 2:
            if len(X) == 1:
                self.constant = y[0]
            else:
                self.constant = Config().default_prediction
            # TODO is this a good default error? should we use the std?
            self.error = Config().var
        else:
            self.model.fit(X, y)
            # TODO should this be on validation data?
            #  We need the score to estimate performance of the whole individual. using validation data would cause an additional loop
            #  using validation data might cause it to bleed over, we should avoid it. in XCS train is used here
            self.error = self.score(X, y, metric=mean_squared_error)
        self.experience = len(y)

    def score(self, X: np.ndarray, y: np.ndarray, metric=None) -> float:
        if metric is None:
            return self.model.score(X, y)
        else:
            return metric(y, self.predict(X))
            #return metric(y, list(map(self.predict, X)))

    def mutate(self):
        raise NotImplementedError()

    @staticmethod
    def random_cl():
        lu = np.sort(Random().random.random((2, Config().xdim)) * 2 - 1, axis=0)
        if Config().cl_min_range:
            diff = lu[1] - lu[0]
            lu[0] -= diff/2
            lu[1] += diff/2
            lu = np.clip(lu, a_max=1, a_min=-1)
        return Classifier(lu[0], lu[1], LinearRegression(), 2)



class Individual:
    def __init__(self, classifiers):
        self.classifiers = classifiers
        self.fitness = None

    def mutate(self):
        raise NotImplementedError()
        # TODO call classifier mutation
        # TODO Add classifier
        # TODO Remove classifier

    def fit(self, X, y):
        # TODO Add note that this does only fit the local models and not optimize classifier location
        for cl in self.classifiers:
            m = cl.matches(X)
            cl.fit(X[np.nonzero(m)], y[np.nonzero(m)])

    def predict(self, X):
        # TODO make this better
        out = np.repeat(Config().default_prediction, X.shape[0])
        if X.ndim == 2:
            for x_idx in range(X.shape[0]):
                x = X[x_idx]
                mixing_sum = 0
                mixing_taus = 0
                for cl in self.classifiers:
                    m = cl.matches(x.reshape((1, -1)))
                    if not m.any():
                        continue
                    mixing_sum += cl.predict(X[np.nonzero(m)])[0]
                    # see drugowich 6.26
                    mixing_taus += 1/(cl.experience - Config().xdim) * cl.error
                if not mixing_sum == 0:
                    out[x_idx] = mixing_sum / mixing_taus
        return out.reshape((-1, 1))

    def parameters(self) -> float:
        # pycharm gives a warning of type missmatch however this seems to work
        return np.sum([cl.degree for cl in self.classifiers])

    @staticmethod
    def random_individual(size):
        return Individual(list(map(lambda x: Classifier.random_cl(),
                                   range(size))))


class LCS:
    def __init__(self, xdim, individuals=None, cl_min_range=None, pop_size=30, ind_size=50, generations=50):
        Config().xdim = xdim
        Config().cl_min_range = cl_min_range
        Config().pop_size = pop_size
        Config().ind_size = ind_size
        Config().generations = generations
        if individuals is None:
            self.population = (list(map(lambda x: Individual.random_individual(
                Config().ind_size), range(Config().pop_size))))
        else:
            self.population = individuals
        self.elitist = None

    def fit(self, X, y):
        Config().default_prediction = np.mean(y)
        Config().var = np.var(y)
        X_train, X_val, y_train, y_val = train_test_split(X, y)

        for ind in self.population:
            ind.fit(X_train, y_train)

        # TODO allow other termination criteria. Early Stopping?
        for i in range(Config().generations):
            pass

    def predict(self, x):
        raise NotImplementedError()


if __name__ == '__main__':
    pass