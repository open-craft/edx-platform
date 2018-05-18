import thunkMiddleware from 'redux-thunk';
import { applyMiddleware, createStore } from 'redux';

import rootReducer from './reducers/index';
import { fetchCSVData } from './actions/csvFetcher';

const store = createStore(
    rootReducer,
    applyMiddleware(thunkMiddleware),
);

const csvUrl = new URLSearchParams(window.location.search).get('csvUrl');

store.dispatch(fetchCSVData(csvUrl));

export default store;
