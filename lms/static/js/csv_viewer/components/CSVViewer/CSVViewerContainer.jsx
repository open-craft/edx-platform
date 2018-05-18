import { connect } from 'react-redux';

import CSVViewer from './CSVViewer.jsx';

const mapStateToProps = state => ({
  rowData: state.csvData.rowData,
  columnDefs: state.csvData.columnDefs,
  error: state.error,
  loading: state.loading,
});

const CSVViewerContainer = connect(mapStateToProps)(CSVViewer);

export default CSVViewerContainer;
