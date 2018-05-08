import React from 'react';

import {Provider} from 'react-redux';
import store from './data/store';
import  {Button} from '@edx/paragon';

import {PopupContainer} from "./components/Popup/PopupContainer";

export const ReportPopup = props => (
    <Provider store={store}>
        <PopupContainer {...props} />
    </Provider>
);
