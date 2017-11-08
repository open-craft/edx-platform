import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';
import { Button } from '@edx/paragon';


class Announcement extends React.Component {
  render() {
    return (
      <div
        className="announcement"
        dangerouslySetInnerHTML={{__html: this.props.content}}
      >
      </div>
    );
  }
}

Announcement.propTypes = {
  content: PropTypes.string.isRequired,
};


class AnnouncementList extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      page: 1,
      announcements: [],
      has_prev: false,
      has_next: false,
    };
  }

  retrievePage(page) {
    $.get('/announcements/page/' + page)
      .then(data => {
        this.setState({
          announcements: data.announcements,
          has_next: data.next,
          has_prev: data.prev,
          page: page
        });
      })
  }

  renderPrevPage() {
    this.retrievePage(this.state.page - 1);
  }

  renderNextPage() {
    this.retrievePage(this.state.page + 1);
  }

  componentWillMount() {
    this.retrievePage(this.state.page);
  }

  render() {
    var children = this.state.announcements.map(
      (announcement, index) => <Announcement key={index} content={announcement.content} />
    );
    if (this.state.has_prev)
    {
      var prev_button = (
        <Button
          className={["announcement-button", "prev"]}
          onClick={() => this.renderPrevPage()}
          label="← previous"
        />
      );
    }
    if (this.state.has_next)
    {
      var next_button = (
        <Button
          className={["announcement-button", "next"]}
          onClick={() => this.renderNextPage()}
          label="next →"
        />
      );
    }
    return (
      <div className="announcements">
        {children}
        {prev_button}
        {next_button}
      </div>
    );
  }
}


export class AnnouncementsView {
  constructor() {
    ReactDOM.render(
      <AnnouncementList />,
      document.getElementById('announcements'),
    );
  }
}
