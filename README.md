# Build analytics for GitLab projects & issues.

The GitLab product has an open [issue](https://gitlab.com/gitlab-org/gitlab/-/issues/7629) to support/add Cumulative Flow Diagrams to their Value Stream Analytics, however, I do not want to wait for an indeterminate timeframe. This [issue](https://gitlab.com/gitlab-org/gitlab/-/issues/7629) and this [issue](https://gitlab.com/gitlab-org/gitlab/-/issues/32422) have been open for over 1-2 years and are currently backlogged.

Using the GitLab [resource state events]( https://docs.gitlab.com/ee/api/resource_state_events.html) API we should be able to build
a tool to access the state events necessary to build a CFD from the ~workflow labels used on our Kanban board.


## Create personal access token

Created an access token here https://gitlab.com/-/profile/personal_access_tokens with expiry in one year, 14 Mar 2022.

I have given this `read_api` permissions, presuming that is enough to query the projects & issues. Access tokens can
be passed as URL parameter (not secure), using the PRIVATE-TOKEN header, or using OAuth2 "Authorization: Bearer <TOKEN>"
headers.

## Resource label events


Third attempt was at [project label events](https://docs.gitlab.com/ee/api/resource_label_events.html#list-project-issue-label-events).

```
$ curl --header "PRIVATE-TOKEN: <TOKEN" https://gitlab.com/api/v4/projects/8279995/issues/191/resource_label_events
[
  {
    "id": 86132274,
    "user": {
      "id": 4941123,
      "name": "Scott Brumbaugh",
      "username": "segfaulter",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/segfaulter"
    },
    "created_at": "2021-02-09T16:59:37.783Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205357,
      "name": "workflow::Designing",
      "color": "#0033CC",
      "description": "Collaborative effort to understand desired outcome and evaluate possible solutions",
      "description_html": "Collaborative effort to understand desired outcome and evaluate possible solutions",
      "text_color": "#FFFFFF"
    },
    "action": "add"
  },
  {
    "id": 86132509,
    "user": {
      "id": 4941123,
      "name": "Scott Brumbaugh",
      "username": "segfaulter",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/segfaulter"
    },
    "created_at": "2021-02-09T17:00:49.416Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205410,
      "name": "workflow::In Progress",
      "color": "#69D100",
      "description": "Developer is implementing code & tests",
      "description_html": "Developer is implementing code &amp; tests",
      "text_color": "#FFFFFF"
    },
    "action": "add"
  },
  {
    "id": 86132510,
    "user": {
      "id": 4941123,
      "name": "Scott Brumbaugh",
      "username": "segfaulter",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/segfaulter"
    },
    "created_at": "2021-02-09T17:00:49.416Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205357,
      "name": "workflow::Designing",
      "color": "#0033CC",
      "description": "Collaborative effort to understand desired outcome and evaluate possible solutions",
      "description_html": "Collaborative effort to understand desired outcome and evaluate possible solutions",
      "text_color": "#FFFFFF"
    },
    "action": "remove"
  },
  {
    "id": 86138921,
    "user": {
      "id": 4941123,
      "name": "Scott Brumbaugh",
      "username": "segfaulter",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/segfaulter"
    },
    "created_at": "2021-02-09T17:36:10.757Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205442,
      "name": "workflow::Code Review",
      "color": "#AD8D43",
      "description": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "description_html": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "text_color": "#FFFFFF"
    },
    "action": "add"
  },
  {
    "id": 86138922,
    "user": {
      "id": 4941123,
      "name": "Scott Brumbaugh",
      "username": "segfaulter",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/segfaulter"
    },
    "created_at": "2021-02-09T17:36:10.757Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205410,
      "name": "workflow::In Progress",
      "color": "#69D100",
      "description": "Developer is implementing code & tests",
      "description_html": "Developer is implementing code &amp; tests",
      "text_color": "#FFFFFF"
    },
    "action": "remove"
  },
  {
    "id": 87396581,
    "user": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "created_at": "2021-02-12T21:36:36.706Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205248,
      "name": "type::Feature",
      "color": "#428BCA",
      "description": "Feature (or Story)",
      "description_html": "Feature (or Story)",
      "text_color": "#FFFFFF"
    },
    "action": "add"
  },
  {
    "id": 91242234,
    "user": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "created_at": "2021-03-03T20:43:11.494Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205410,
      "name": "workflow::In Progress",
      "color": "#69D100",
      "description": "Developer is implementing code & tests",
      "description_html": "Developer is implementing code &amp; tests",
      "text_color": "#FFFFFF"
    },
    "action": "add"
  },
  {
    "id": 91242550,
    "user": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "created_at": "2021-03-03T20:47:05.876Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205442,
      "name": "workflow::Code Review",
      "color": "#AD8D43",
      "description": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "description_html": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "text_color": "#FFFFFF"
    },
    "action": "remove"
  },
  {
    "id": 91881229,
    "user": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "created_at": "2021-03-07T03:20:57.234Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205442,
      "name": "workflow::Code Review",
      "color": "#AD8D43",
      "description": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "description_html": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "text_color": "#FFFFFF"
    },
    "action": "add"
  },
  {
    "id": 91881230,
    "user": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "created_at": "2021-03-07T03:20:57.234Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205410,
      "name": "workflow::In Progress",
      "color": "#69D100",
      "description": "Developer is implementing code & tests",
      "description_html": "Developer is implementing code &amp; tests",
      "text_color": "#FFFFFF"
    },
    "action": "remove"
  },
  {
    "id": 92165763,
    "user": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "created_at": "2021-03-08T20:03:55.756Z",
    "resource_type": "Issue",
    "resource_id": 77308044,
    "label": {
      "id": 18205442,
      "name": "workflow::Code Review",
      "color": "#AD8D43",
      "description": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "description_html": "Developer has published merge request and is actively resolving comments and issues raised by team",
      "text_color": "#FFFFFF"
    },
    "action": "remove"
  }
]
```


## Resource state events

First look was at resource state events but this only includes created and closed.

```
$ curl --header "PRIVATE-TOKEN: <TOKEN>" https://gitlab.com/api/v4/projects/8279995/issues/24/resource_state_events
[
  {
    "id": 25457645,
    "user": {
      "id": 2768090,
      "name": "Tyson",
      "username": "tysonholub",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/2768090/avatar.png",
      "web_url": "https://gitlab.com/tysonholub"
    },
    "created_at": "2021-03-09T17:59:43.041Z",
    "resource_type": "Issue",
    "resource_id": 30436752,
    "state": "closed"
  }
]
```

## Group issue list

Second look is at querying group level issues by milestone. Sample output is filtered to 2 items that include our
~workflow label transitions. The output **does not** show label transition details. So we will add `with_labels_details=true` options.


```
$ curl --header "PRIVATE-TOKEN: <TOKEN>" https://gitlab.com/api/v4/groups/gozynta/issues?milestone=mb_v1.3\&iids=24,191\&with_labels_details=true
[
  {
    "id": 77308044,
    "iid": 191,
    "project_id": 8279995,
    "title": "Tab description still says \"Mobius Connect\"",
    "description": "Change this to Gozynta Mobius.\n![image](/uploads/cbc4ca550190daa19715be58ef27643f/image.png)\n\nAlso search the codebase for other references to Mobius Connect.  I assume we want to change them all to Gozynta Mobius, but check with me if there's any uncertainty about any of them.",
    "state": "closed",
    "created_at": "2021-01-15T18:12:49.349Z",
    "updated_at": "2021-03-08T20:03:55.687Z",
    "closed_at": "2021-03-08T18:42:53.488Z",
    "closed_by": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "labels": [
      {
        "id": 18205248,
        "name": "type::Feature",
        "color": "#428BCA",
        "description": "Feature (or Story)",
        "description_html": "Feature (or Story)",
        "text_color": "#FFFFFF"
      }
    ],
    "milestone": {
      "id": 1905585,
      "iid": 6,
      "group_id": 3505831,
      "title": "mb_v1.3",
      "description": "Mobius 1.3 release milestone",
      "state": "active",
      "created_at": "2021-02-22T21:21:59.908Z",
      "updated_at": "2021-02-22T21:21:59.908Z",
      "due_date": "2021-03-31",
      "start_date": "2021-01-01",
      "expired": false,
      "web_url": "https://gitlab.com/groups/gozynta/-/milestones/6"
    },
    "assignees": [
      {
        "id": 7849475,
        "name": "Andrew Hamlin",
        "username": "andrew360",
        "state": "active",
        "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
        "web_url": "https://gitlab.com/andrew360"
      }
    ],
    "author": {
      "id": 934686,
      "name": "Brian Johnson",
      "username": "sherbang",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/34cce02fd96a04fa7565f53ea77e5249?s=80&d=identicon",
      "web_url": "https://gitlab.com/sherbang"
    },
    "assignee": {
      "id": 7849475,
      "name": "Andrew Hamlin",
      "username": "andrew360",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/7849475/avatar.png",
      "web_url": "https://gitlab.com/andrew360"
    },
    "user_notes_count": 8,
    "merge_requests_count": 1,
    "upvotes": 0,
    "downvotes": 0,
    "due_date": null,
    "confidential": false,
    "discussion_locked": null,
    "web_url": "https://gitlab.com/gozynta/cwacc/-/issues/191",
    "time_stats": {
      "time_estimate": 0,
      "total_time_spent": 0,
      "human_time_estimate": null,
      "human_total_time_spent": null
    },
    "task_completion_status": {
      "count": 0,
      "completed_count": 0
    },
    "weight": null,
    "blocking_issues_count": 0,
    "has_tasks": false,
    "_links": {
      "self": "https://gitlab.com/api/v4/projects/8279995/issues/191",
      "notes": "https://gitlab.com/api/v4/projects/8279995/issues/191/notes",
      "award_emoji": "https://gitlab.com/api/v4/projects/8279995/issues/191/award_emoji",
      "project": "https://gitlab.com/api/v4/projects/8279995"
    },
    "references": {
      "short": "#191",
      "relative": "cwacc#191",
      "full": "gozynta/cwacc#191"
    },
    "moved_to_id": null,
    "service_desk_reply_to": null,
    "epic_iid": null,
    "epic": null
  },
  {
    "id": 30436752,
    "iid": 24,
    "project_id": 8279995,
    "title": "Batch status: infinite scroll records repeated with different times",
    "description": "On initial page load html is returned from the server,\n```\n<li>\n\t<a href=\"/user/batch_status/1372402\">\n\t\t<strong>[9130347522106456] AutoSyncModule Create Batch &#34;Inventory Batch&#34;</strong><br/>\n\t\tFeb 05, 2020 11:08 AM<br/>\n\t\t<span>an hour ago</span>\n\t</a>\n</li>\n```\nUser scrolls down, at bottom ajax request for more data is made and server returns json with the same records.  Records are duplicated and time is rendered differently.\n\n```\n{results: [{created: \"Wed, 05 Feb 2020 16:08:23 GMT\", format_datetime: \"Feb 05, 2020 04:08 PM\",…},…]}\n...\ncreated: \"Wed, 05 Feb 2020 16:08:23 GMT\"\nformat_datetime: \"Feb 05, 2020 04:08 PM\"\nformat_humanize: \"an hour ago\"\nname: \"[9130347522106456] AutoSyncModule Create Batch \"Inventory Batch\"\"\nstatus: 4\ntask_id: 1372402\nurl: \"/user/batch_status/1372402\"\n```",
    "state": "closed",
    "created_at": "2020-02-05T17:29:48.217Z",
    "updated_at": "2021-03-17T18:14:59.238Z",
    "closed_at": "2021-03-09T17:59:42.952Z",
    "closed_by": {
      "id": 2768090,
      "name": "Tyson",
      "username": "tysonholub",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/2768090/avatar.png",
      "web_url": "https://gitlab.com/tysonholub"
    },
    "labels": [
      {
        "id": 18205251,
        "name": "type::Bug",
        "color": "#CC0033",
        "description": "Bug (or Defect)",
        "description_html": "Bug (or Defect)",
        "text_color": "#FFFFFF"
      }
    ],
    "milestone": {
      "id": 1905585,
      "iid": 6,
      "group_id": 3505831,
      "title": "mb_v1.3",
      "description": "Mobius 1.3 release milestone",
      "state": "active",
      "created_at": "2021-02-22T21:21:59.908Z",
      "updated_at": "2021-02-22T21:21:59.908Z",
      "due_date": "2021-03-31",
      "start_date": "2021-01-01",
      "expired": false,
      "web_url": "https://gitlab.com/groups/gozynta/-/milestones/6"
    },
    "assignees": [
      {
        "id": 2768090,
        "name": "Tyson",
        "username": "tysonholub",
        "state": "active",
        "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/2768090/avatar.png",
        "web_url": "https://gitlab.com/tysonholub"
      }
    ],
    "author": {
      "id": 4941123,
      "name": "Scott Brumbaugh",
      "username": "segfaulter",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/segfaulter"
    },
    "assignee": {
      "id": 2768090,
      "name": "Tyson",
      "username": "tysonholub",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/2768090/avatar.png",
      "web_url": "https://gitlab.com/tysonholub"
    },
    "user_notes_count": 1,
    "merge_requests_count": 0,
    "upvotes": 0,
    "downvotes": 0,
    "due_date": null,
    "confidential": false,
    "discussion_locked": null,
    "web_url": "https://gitlab.com/gozynta/cwacc/-/issues/24",
    "time_stats": {
      "time_estimate": 0,
      "total_time_spent": 0,
      "human_time_estimate": null,
      "human_total_time_spent": null
    },
    "task_completion_status": {
      "count": 0,
      "completed_count": 0
    },
    "weight": null,
    "blocking_issues_count": 0,
    "has_tasks": false,
    "_links": {
      "self": "https://gitlab.com/api/v4/projects/8279995/issues/24",
      "notes": "https://gitlab.com/api/v4/projects/8279995/issues/24/notes",
      "award_emoji": "https://gitlab.com/api/v4/projects/8279995/issues/24/award_emoji",
      "project": "https://gitlab.com/api/v4/projects/8279995"
    },
    "references": {
      "short": "#24",
      "relative": "cwacc#24",
      "full": "gozynta/cwacc#24"
    },
    "moved_to_id": null,
    "service_desk_reply_to": null,
    "epic_iid": null,
    "epic": null
  }
]
```
