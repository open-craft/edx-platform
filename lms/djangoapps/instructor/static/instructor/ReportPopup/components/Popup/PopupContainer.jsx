import {connect} from 'react-redux';
import Popup from "./Popup";

const mapStateToProps = state => ({
    showPopup: state.showPopup
});


const mapDispatchToProps = dispatch => ({

});

const PopupContainer = connect(
    mapStateToProps,
    mapDispatchToProps,
)(Popup);

export default PopupContainer;
