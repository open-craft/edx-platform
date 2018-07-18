/* global gettext */
import { Button } from '@edx/paragon/static';
import { AgGridReact } from 'ag-grid-react';
import * as PropTypes from 'prop-types';
import * as React from 'react';

const CSVViewer = ({
                     columnDefs,
                     csvUrl,
                     enableRtl,
                     error,
                     errorMessages,
                     loading,
                     loadingMessage,
                     rowData,
                   }) => {
  if (error) {
    return (
      <div className="csv-viewer-grid error-message">
        {errorMessages[error] || error}
      </div>
    );
  }
  if (loading) {
    return (
      <div className="csv-viewer-grid loading-message">
        {loadingMessage}
      </div>
    );
  }
  return (
    <div className="csv-viewer-main">
      <div className="download-button-row">
        <Button
          label={gettext('Download CSV')}
          onClick={() => window.open(csvUrl)}
        />
      </div>
      <div className="csv-viewer-grid ag-theme-fresh">
        <AgGridReact
          enableSorting
          enableFilter
          enableColResize
          enableRtl={enableRtl}
          columnDefs={columnDefs}
          defaultColDef={{ autoHeight: true, filter: 'agTextColumnFilter' }}
          rowData={rowData}
        />
      </div>
    </div>
  );
};

CSVViewer.propTypes = {
  columnDefs: PropTypes.arrayOf(PropTypes.object),
  csvUrl: PropTypes.string.isRequired,
  enableRtl: PropTypes.bool,
  error: PropTypes.string,
  errorMessages: PropTypes.objectOf(PropTypes.string),
  loading: PropTypes.bool,
  loadingMessage: PropTypes.string,
  rowData: PropTypes.arrayOf(PropTypes.shape({
    field: PropTypes.string.isRequired,
  })),
};

CSVViewer.defaultProps = {
  columnDefs: [],
  enableRtl: false,
  error: null,
  errorMessages: null,
  loading: false,
  loadingMessage: null,
  rowData: [],
};

export default CSVViewer;
