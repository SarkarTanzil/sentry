from __future__ import absolute_import

import datetime
import six
from collections import namedtuple

from django.db.models import Avg, Count
from django.utils import timezone

from rest_framework.response import Response

from sentry.api.bases.project import ProjectEndpoint, ProjectReleasePermission
from sentry.app import tsdb
from sentry.models import Deploy, Environment, Release, ReleaseProject

StatsPeriod = namedtuple('StatsPeriod', ('segments', 'interval'))


class ProjectReleaseStatsEndpoint(ProjectEndpoint):
    permission_classes = (ProjectReleasePermission,)

    STATS_PERIODS = {
        '24h': StatsPeriod(24, datetime.timedelta(hours=1)),
        '30d': StatsPeriod(30, datetime.timedelta(hours=24)),
    }

    def get(self, request, project):
        # avg num authors per release
        avg_num_authors = Release.objects.filter(
            projects=project,
            organization_id=project.organization_id,
        ).annotate(
            num_authors=Count('releasecommit__commit__author'),
        ).aggregate(Avg('num_authors'))['num_authors__avg']

        # time to release (avg time between releases)
        sum_deltas = datetime.timedelta(seconds=0)
        release_dates = list(Release.objects.filter(
            projects=project,
            organization_id=project.organization_id,
        ).order_by('date_added').values_list('date_added', flat=True))

        for i, date_added in enumerate(release_dates):
            try:
                next_date = release_dates[i + 1]
            except IndexError:
                pass
            else:
                sum_deltas += (next_date - date_added)

        releases = list(Release.objects.filter(
            projects=project,
            organization_id=project.organization_id,
        ).order_by('-date_added').values('id', 'version'))
        versions_by_id = {
            r['id']: r['version']
            for r in releases
        }

        # avg new groups per release
        avg_new_groups = ReleaseProject.objects.filter(
            project=project,
        ).aggregate(Avg('new_groups'))['new_groups__avg']

        items = {
            project.id: versions_by_id.keys(),
        }

        until = timezone.now()
        stats = {}
        for key, (segments, interval) in six.iteritems(self.STATS_PERIODS):
            since = until - (segments * interval)

            _stats = tsdb.get_frequency_series(
                model=tsdb.models.frequent_releases_by_project,
                items=items,
                start=since,
                end=until,
                rollup=int(interval.total_seconds()),
            )
            stats[key] = [
                (item[0], {versions_by_id[r_id]: count for r_id, count in item[1].items()})
                for item in _stats.get(project.id, [])]

        deploys = list(Deploy.objects.filter(
            organization_id=project.organization_id,
            release_id__in=versions_by_id.keys(),
            date_finished__gt=until - datetime.timedelta(days=30),
        ).values('date_finished', 'environment_id', 'release_id'))

        environments = {
            env.id: env.name
            for env in Environment.objects.filter(
                organization_id=project.organization_id,
                id__in=[d['environment_id'] for d in deploys]
            )
        }

        return Response({
            'AvgNumAuthors': avg_num_authors,
            'AvgNewGroups': avg_new_groups,
            'AvgTimeToRelease': (sum_deltas / len(release_dates)).total_seconds() * 1000,
            'CountReleases': len(release_dates),
            'releases': releases,
            'stats': stats,
            'deploys': [{
                'environment': environments[d['environment_id']],
                'release': versions_by_id[d['release_id']],
                'dateFinished': int(d['date_finished'].strftime('%s')),
            } for d in deploys],
        })