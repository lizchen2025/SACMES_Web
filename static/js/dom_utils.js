export function getById(id, { required = false, root = document } = {}) {
    const element = root.getElementById(id);
    if (!element && required) {
        console.warn(`[DOM] Missing required element: #${id}`);
    }
    return element;
}

export function getAll(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
}

export function bindIfPresent(target, eventName, handler, options) {
    if (!target) {
        return false;
    }

    if (typeof target.forEach === 'function' && !target.addEventListener) {
        target.forEach((item) => bindIfPresent(item, eventName, handler, options));
        return true;
    }

    target.addEventListener(eventName, handler, options);
    return true;
}

export function setTextIfPresent(element, text) {
    if (element) {
        element.textContent = text;
    }
}

export function setClassNameIfPresent(element, className) {
    if (element) {
        element.className = className;
    }
}

export function clearChildren(element) {
    if (element) {
        element.replaceChildren();
    }
}

export function resetSelectOptions(select, placeholderLabel = 'Select', placeholderValue = '') {
    if (!select) {
        return;
    }

    const placeholder = new Option(placeholderLabel, placeholderValue);
    select.replaceChildren(placeholder);
}

export function setSingleMessage(element, text, className = '') {
    if (!element) {
        return;
    }

    const message = document.createElement('p');
    if (className) {
        message.className = className;
    }
    message.textContent = text;
    element.replaceChildren(message);
}

export function setSelectOptions(select, options) {
    if (!select) {
        return;
    }

    const fragments = options.map(({ label, value }) => new Option(label, value));
    select.replaceChildren(...fragments);
}
