import {applyMiddleware, createStore} from 'redux';
import thunkMiddleware from 'redux-thunk';

import rootReducer from './reducers/index';

const configureStore = initialState => createStore(
    rootReducer,
    initialState,
    applyMiddleware(thunkMiddleware)
);


const store = configureStore();

export default store;
