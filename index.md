---
layout: default
title: "Latest Posts"
---

<div class="post-list">
  {% for post in site.posts %}
    <div class="post-item">
      <a class="post-link" href="{{ post.url | relative_url }}">{{ post.title }}</a>
      <div class="post-meta">{{ post.date | date: "%B %d, %Y" }}</div>
    </div>
  {% endfor %}
</div>
