import * as React from 'react';
import * as PropTypes from 'prop-types';
import {Modal, Button} from '@edx/paragon';

export default class Popup extends React.Component {
    handleTogglePopup() {
        this.setState({showPopup: !this.state.showDropdown});
    }

    hidePopup() {
        this.setState({showPopup: false});
    }

    render() {
        const modalProps = {
            body: "Test",
            buttons: [
                <Button label={gettext("View report")}/>,
                <Button label={gettext("Download CSV")}/>
            ],
            onClose: this.hidePopup
        };

        return (
            <div>
                <Button onClick={this.handleTogglePopup}
                        name="list-problem-responses-csv" label={gettext("Download a CSV of problem responses")}
                />
                <Modal title="Learner Response Report" {...modalProps}>

                </Modal>
            </div>
        );
    }
}

Popup.propTypes = {
};