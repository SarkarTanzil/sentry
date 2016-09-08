import React from 'react';
import ApiMixin from '../mixins/apiMixin';
import IndicatorStore from '../stores/indicatorStore';
import LoadingIndicator from '../components/loadingIndicator';
import plugins from '../plugins';
import {t} from '../locale';

const PluginConfig = React.createClass({
  propTypes: {
    organization: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
    data: React.PropTypes.object.isRequired,
    onDisablePlugin: React.PropTypes.func,
  },

  mixins: [ApiMixin],

  getDefaultProps() {
    return {
      onDisablePlugin: window.location.reload
    };
  },

  componentWillMount() {
    this.loadPlugin(this.props.data);
  },

  componentWillReceiveProps(nextProps) {
    this.loadPlugin(nextProps.data);
  },

  loadPlugin(data) {
    this.setState({
      loading: true,
    }, () => {
      plugins.load(data, () => {
        this.setState({loading: false});
      });
    });
  },

  getPluginEndpoint() {
    let {organization, project, data} = this.props;
    return (
      `/projects/${organization.slug}/${project.slug}/plugins/${data.id}/`
    );
  },

  disablePlugin() {
    let loadingIndicator = IndicatorStore.add(t('Saving changes..'));
    this.api.request(this.getPluginEndpoint(), {
      method: 'DELETE',
      success: () => {
        this.props.onDisablePlugin();
        IndicatorStore.remove(loadingIndicator);
      },
      error: (error) => {
        IndicatorStore.add(t('Unable to disable plugin. Please try again.'), 'error');
      }
    });
  },

  render() {
    let data = this.props.data;

            // <button className="btn btn-sm btn-default pull-right"
            //         onClick={this.disablePlugin.bind(this, data)}>{t('Disable')}</button>}
    return (
      <div className="box">
        <div className="box-header">
          {data.canDisable && data.enabled &&
            <div className="pull-right">
              <a className="btn btn-sm btn-default"
                 onClick={this.disablePlugin}>{t('Disable')}</a>
            </div>
          }
          <h3>{data.name}</h3>
        </div>
        <div className="box-content with-padding">
          {this.state.loading ?
            <LoadingIndicator />
          :
            plugins.get(data).renderSettings({
              organization: this.props.organization,
              project: this.props.project,
            })
          }
        </div>
      </div>
    );
  }
});

export default PluginConfig;