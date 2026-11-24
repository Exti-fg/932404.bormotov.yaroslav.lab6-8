const PAGE_SIZE = 6;

const state = {
    page: 1,
    sort: "desc",
    posts: [],
    activePost: null,
};

const elements = {
    list: document.querySelector("#post-list"),
    pagination: document.querySelector("#pagination"),
    status: document.querySelector("#status-message"),
    sort: document.querySelector("#sort-order"),
    postDialog: document.querySelector("#post-dialog"),
    postForm: document.querySelector("#post-form"),
    postId: document.querySelector("#post-id"),
    postTitle: document.querySelector("#post-title"),
    postContent: document.querySelector("#post-content"),
    postError: document.querySelector("#post-error"),
    storyDialog: document.querySelector("#story-dialog"),
    commentDialog: document.querySelector("#comment-dialog"),
    commentForm: document.querySelector("#comment-form"),
    commentError: document.querySelector("#comment-error"),
    toast: document.querySelector("#toast"),
};

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[character]);
}

function formatDate(value) {
    return new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
    }).format(new Date(value));
}

function formatCommentCount(count) {
    const category = new Intl.PluralRules("ru-RU").select(count);
    const noun = { one: "комментарий", few: "комментария", many: "комментариев" }[category];
    return `${count} ${noun}`;
}

function excerpt(content) {
    const text = content.trim();
    return text.length > 190 ? `${text.slice(0, 190).trimEnd()}…` : text;
}

async function request(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers,
        },
    });
    if (!response.ok) {
        let message = `Ошибка запроса (${response.status}).`;
        try {
            const body = await response.json();
            message = body.detail || message;
        } catch {
            // Keep the HTTP status message when the server returned no JSON.
        }
        throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
}

function createPostCard(post) {
    const card = document.createElement("article");
    card.className = "post-card";
    card.innerHTML = `
        <div class="post-meta">
            <time datetime="${escapeHTML(post.published_at)}">${escapeHTML(formatDate(post.published_at))}</time>
            <span class="comment-count"><span aria-hidden="true">◌</span> ${post.comments_count}</span>
        </div>
        <h3>${escapeHTML(post.title)}</h3>
        <p class="post-excerpt">${escapeHTML(excerpt(post.content))}</p>
        <button class="read-link" type="button" data-post-id="${post.id}">
            Читать историю <span aria-hidden="true">↗</span>
        </button>`;
    return card;
}

function renderPagination(pages) {
    elements.pagination.replaceChildren();
    if (pages <= 1) return;

    const previous = document.createElement("button");
    previous.type = "button";
    previous.className = "page-button page-arrow";
    previous.textContent = "←";
    previous.setAttribute("aria-label", "Предыдущая страница");
    previous.disabled = state.page === 1;
    previous.addEventListener("click", () => loadPosts(state.page - 1));
    elements.pagination.append(previous);

    for (let page = 1; page <= pages; page += 1) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "page-button";
        button.textContent = String(page);
        button.setAttribute("aria-label", `Страница ${page}`);
        if (page === state.page) button.setAttribute("aria-current", "page");
        button.addEventListener("click", () => loadPosts(page));
        elements.pagination.append(button);
    }

    const next = document.createElement("button");
    next.type = "button";
    next.className = "page-button page-arrow";
    next.textContent = "→";
    next.setAttribute("aria-label", "Следующая страница");
    next.disabled = state.page === pages;
    next.addEventListener("click", () => loadPosts(state.page + 1));
    elements.pagination.append(next);
}

async function loadPosts(page = 1) {
    state.page = page;
    elements.list.setAttribute("aria-busy", "true");
    elements.status.textContent = "";
    try {
        const result = await request(
            `/api/posts?page=${state.page}&limit=${PAGE_SIZE}&sort=${state.sort}`,
        );
        if (result.pages > 0 && state.page > result.pages) {
            return loadPosts(result.pages);
        }
        state.posts = result.items;
        elements.list.replaceChildren(...state.posts.map(createPostCard));
        elements.list.classList.toggle("is-empty", result.total === 0);
        if (result.total === 0) {
            elements.list.innerHTML = `
                <div class="empty-state">
                    <span aria-hidden="true">✳</span>
                    <h3>Здесь появится первая история</h3>
                    <p>Нажмите «Новая запись» и поделитесь тем, что вас вдохновило.</p>
                </div>`;
        }
        renderPagination(result.pages);
    } catch (error) {
        elements.status.textContent = error.message;
    } finally {
        elements.list.setAttribute("aria-busy", "false");
    }
}

function notify(message) {
    elements.toast.textContent = message;
    elements.toast.classList.add("is-visible");
    window.setTimeout(() => elements.toast.classList.remove("is-visible"), 2800);
}

function openPostForm(post = null) {
    elements.postForm.reset();
    elements.postError.textContent = "";
    elements.postId.value = post ? post.id : "";
    elements.postTitle.value = post ? post.title : "";
    elements.postContent.value = post ? post.content : "";
    document.querySelector("#post-dialog-title").textContent = post ? "Редактировать историю" : "Новая запись";
    elements.postDialog.showModal();
    elements.postTitle.focus();
}

async function openStory(postId) {
    try {
        const post = await request(`/api/posts/${postId}`);
        state.activePost = post;
        document.querySelector("#story-title").textContent = post.title;
        document.querySelector("#story-date").textContent = formatDate(post.published_at);
        document.querySelector("#story-content").textContent = post.content;
        document.querySelector("#story-comment-count").textContent = formatCommentCount(post.comments_count);
        if (!elements.storyDialog.open) elements.storyDialog.showModal();
        await loadComments(post.id);
    } catch (error) {
        notify(error.message);
    }
}

async function loadComments(postId) {
    const list = document.querySelector("#comments-list");
    list.setAttribute("aria-busy", "true");
    try {
        const comments = await request(`/api/posts/${postId}/comments`);
        document.querySelector("#comments-total").textContent = `(${comments.length})`;
        document.querySelector("#story-comment-count").textContent = formatCommentCount(comments.length);
        if (comments.length === 0) {
            list.innerHTML = '<p class="no-comments">Пока тихо. Будьте первым, кто оставит комментарий.</p>';
        } else {
            list.replaceChildren(...comments.map((comment) => {
                const item = document.createElement("article");
                item.className = "comment-item";
                item.innerHTML = `
                    <div class="comment-avatar" aria-hidden="true">${escapeHTML(comment.author.trim().slice(0, 1).toUpperCase())}</div>
                    <div>
                        <div class="comment-author">${escapeHTML(comment.author)}
                            <time datetime="${escapeHTML(comment.created_at)}">${escapeHTML(formatDate(comment.created_at))}</time>
                        </div>
                        <p>${escapeHTML(comment.text)}</p>
                    </div>`;
                return item;
            }));
        }
    } catch (error) {
        list.textContent = error.message;
    } finally {
        list.setAttribute("aria-busy", "false");
    }
}

document.querySelector("#new-post").addEventListener("click", () => openPostForm());
elements.sort.addEventListener("change", () => {
    state.sort = elements.sort.value;
    loadPosts(1);
});

elements.list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-post-id]");
    if (button) openStory(Number(button.dataset.postId));
});

elements.postForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    elements.postError.textContent = "";
    const id = elements.postId.value;
    const body = JSON.stringify({
        title: elements.postTitle.value,
        content: elements.postContent.value,
    });
    try {
        await request(id ? `/api/posts/${id}` : "/api/posts", {
            method: id ? "PUT" : "POST",
            body,
        });
        elements.postDialog.close();
        notify(id ? "История обновлена." : "История опубликована.");
        await loadPosts(id ? state.page : 1);
        if (id && state.activePost) await openStory(Number(id));
    } catch (error) {
        elements.postError.textContent = error.message;
    }
});

document.querySelector("#edit-post").addEventListener("click", () => {
    if (!state.activePost) return;
    const post = state.activePost;
    elements.storyDialog.close();
    openPostForm(post);
});

document.querySelector("#delete-post").addEventListener("click", async () => {
    if (!state.activePost || !window.confirm("Удалить эту запись вместе со всеми комментариями?")) return;
    try {
        await request(`/api/posts/${state.activePost.id}`, { method: "DELETE" });
        elements.storyDialog.close();
        state.activePost = null;
        notify("Запись удалена.");
        await loadPosts(state.page);
    } catch (error) {
        notify(error.message);
    }
});

document.querySelector("#story-comment").addEventListener("click", () => {
    if (!state.activePost) return;
    elements.commentForm.reset();
    elements.commentError.textContent = "";
    elements.commentDialog.showModal();
    document.querySelector("#comment-author").focus();
});

elements.commentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    elements.commentError.textContent = "";
    try {
        await request(`/api/posts/${state.activePost.id}/comments`, {
            method: "POST",
            body: JSON.stringify({
                author: document.querySelector("#comment-author").value,
                text: document.querySelector("#comment-text").value,
            }),
        });
        elements.commentDialog.close();
        notify("Комментарий опубликован.");
        await openStory(state.activePost.id);
        await loadPosts(state.page);
    } catch (error) {
        elements.commentError.textContent = error.message;
    }
});

document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => document.getElementById(button.dataset.close).close());
});

document.querySelectorAll(".dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
    });
});

loadPosts();
