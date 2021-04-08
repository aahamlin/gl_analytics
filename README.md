# Build analytics for GitLab projects & issues.

The GitLab product has an open [issue](https://gitlab.com/gitlab-org/gitlab/-/issues/7629) to support/add Cumulative Flow Diagrams to their Value Stream Analytics, however, I do not want to wait for an indeterminate timeframe. This [issue](https://gitlab.com/gitlab-org/gitlab/-/issues/7629) and this [issue](https://gitlab.com/gitlab-org/gitlab/-/issues/32422) have been open for over 1-2 years and are currently backlogged.

Using the GitLab [resource state events](https://docs.gitlab.com/ee/api/resource_state_events.html) API we should be able to build
a tool to access the state events necessary to build a CFD from the ~workflow labels used on our Kanban board.


## Usage

No installer yet.

```
$ pipenv run python -m gl_analytics --help
$ pipenv run python -m gl_analytics --milestone mb_v1.3 --days 30
```



## Todos

- Create installable (setup.cfg or newer toml format?)
- Add output/export class(es) for generating Images, CSV, etc
- Refactor areas marked with XXX comments
- generating plot images directly, rather than importing CSV into a spreadsheet

Work in Progress: Using `matplotlib` to product images directly. Given a DataFrame `df`, generating a diagram and saving
to a file is straight forward.

```
    import matplotlib.pyplot as plt
    plt.close("all")
    ax = df.plot.area()
    fig = ax.get_figure()
    fig.savefig('output.png')
```

## Create personal access token

Created an access token here https://gitlab.com/-/profile/personal_access_tokens with expiry in one year, 14 Mar 2022.

I have given this `read_api` permissions, presuming that is enough to query the projects & issues. Access tokens can
be passed as URL parameter (not secure), using the PRIVATE-TOKEN header, or using OAuth2 "Authorization: Bearer <TOKEN>"
headers.

## Group issues, pagination

We can retrieve pages of issues filtered by (group) milestones. Using the `link` response header to traverse the page.

```
$ curl -i --header "PRIVATE-TOKEN: <TOKEN>" https://gitlab.com/api/v4/groups/gozynta/issues?pagination=keyset&per_page=5&milestone=mb_v1.3
HTTP/2 200
date: Thu, 18 Mar 2021 14:46:11 GMT
content-type: application/json
set-cookie: __cfduid=d0d6371e9c7139653518ee29b035bf5ba1616078771; expires=Sat, 17-Apr-21 14:46:11 GMT; path=/; domain=.gitlab.com; HttpOnly; SameSite=Lax; Secure
vary: Accept-Encoding
cache-control: max-age=0, private, must-revalidate
etag: W/"458780b10fd5d4a50de8801127b66020"
link: <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=2&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="next", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=1&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="first", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=9&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="last"
...

[{"id":80750993,"iid":264,"project_id":8279995," ...
```

## Resource label events

Now with the list of issue iid values we can use [project label events](https://docs.gitlab.com/ee/api/resource_label_events.html#list-project-issue-label-events)
to build our CFD dataset.

> Note this example requires knowing the project id. There is probably a way to retrieve by project/group names.

```
$ curl --header "PRIVATE-TOKEN: <TOKEN" https://gitlab.com/api/v4/projects/8279995/issues/191/resource_label_events
[
  {
    "id": 86132274,
    "user": {
      "id": 4941123,
      "name": "Nobody",
      "username": "nobody_username",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/nobody_username"
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
      "name": "Nobody",
      "username": "nobody_username",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/nobody_username"
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
      "name": "Nobody",
      "username": "nobody_username",
      "state": "active",
      "avatar_url": "https://secure.gravatar.com/avatar/aa00c8fa6a966ce402cf12c46ce9831e?s=80&d=identicon",
      "web_url": "https://gitlab.com/nobody_username"
    },
    "created_at": "2021-02-09T17:00:49.416Z",
    "resource_type": "Issue",
    "resource_id": 77308044,1
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
  ...
]
```


# Other notes

## Resource state events

First look was at resource state events but this only includes created and closed events. These are available in the
issues themselves via the opened\_at and closed\_at fields.

```
{
    "id": 80750993,
    "iid": 264,
    "project_id": 8279995,
    "title": "Upgrade machine type of cloudsql instances",
    "description": "..."
    "state": "opened",
    "created_at": "2021-03-11T19:24:21.913Z",
    "updated_at": "2021-03-16T21:14:37.454Z",
    "closed_at": null,
    "closed_by": null,
    "labels": [
      "type::Chore",
      "workflow::Ready"
    ],
```

So there does not seem to be a need to parse the state events.

```
$ curl --header "PRIVATE-TOKEN: <TOKEN>" https://gitlab.com/api/v4/projects/8279995/issues/24/resource_state_events
[
  {
    "id": 25457645,
    "user": {
      "id": 2768090,
      "name": "Nobody",
      "username": "nobody_username",
      "state": "active",
      "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/2768090/avatar.png",
      "web_url": "https://gitlab.com/nobody_username"
    },
    "created_at": "2021-03-09T17:59:43.041Z",
    "resource_type": "Issue",
    "resource_id": 30436752,
    "state": "closed"
  }
]
```
