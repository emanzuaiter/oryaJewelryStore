window.ORYA = window.ORYA || {};

// Toast notifications
ORYA.toast = function (message, type, duration) {
  type     = type     || 'default';
  duration = duration !== undefined ? duration : 3000;

  var toast = document.createElement('div');
  toast.className = 'toast' + (type !== 'default' ? ' toast-' + type : '');
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      toast.classList.add('toast-show');
    });
  });

  setTimeout(function () {
    toast.classList.remove('toast-show');
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, duration);
};

// Fetch wrapper
ORYA.fetch = async function (url, options) {
  options = options || {};

  var defaults = {
    headers: {
      'Content-Type':     'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    }
  };

  var config = Object.assign({}, defaults, options);
  config.headers = Object.assign({}, defaults.headers, options.headers || {});

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  var response = await fetch(url, config);
  return response.json();
};

// Format price in JOD
ORYA.formatPrice = function (amount) {
  return parseFloat(amount).toFixed(3) + ' JOD';
};

// Generate / retrieve guest session ID
ORYA.getSessionId = function () {
  var sid = sessionStorage.getItem('orya_session');
  if (!sid) {
    sid = 'guest_' + Date.now() + '_' +
          Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('orya_session', sid);
  }
  return sid;
};

// Debounce
ORYA.debounce = function (fn, delay) {
  var timer;
  return function () {
    var args    = arguments;
    var context = this;
    clearTimeout(timer);
    timer = setTimeout(function () {
      fn.apply(context, args);
    }, delay);
  };
};
