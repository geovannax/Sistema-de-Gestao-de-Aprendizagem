
function showNotificationPopup(tag, message) {

  if (tag === 'Error' || tag === 'Warning') {
    var sleep = 15000;
  } else{
    var sleep = 5000;
  }

  var popup = document.getElementById('notification-popup');

  var notification = document.createElement('div');
  notification.className = 'notification';

  var titleNotification = document.createElement('div');
  titleNotification.classList.add('d-flex','justify-content-between','title-notification', tag);
  titleNotification.innerHTML = tag; 

  var iconClose = document.createElement('i');
  iconClose.className = 'bi bi-x-lg';

  var closeButton = document.createElement('button');
  closeButton.classList.add('notification-close-button');
  closeButton.addEventListener('click', function() {
    notification.style.display = 'none';
  });
  closeButton.appendChild(iconClose);
  titleNotification.appendChild(closeButton);
  
  var contentNotification = document.createElement('div');
  contentNotification.className = 'content-notification';
  contentNotification.innerHTML = message.replaceAll('. ', '.<br/>');

  notification.appendChild(titleNotification);
  notification.appendChild(contentNotification);
  popup.appendChild(notification);
  popup.style.display = 'block';

  var opacity = 0;
  var interval = setInterval(function() {
    opacity += 0.1;
    popup.style.opacity = opacity;
    if (opacity >= 1) {
      clearInterval(interval);
      setTimeout(function() {
        var interval = setInterval(function() {
          opacity -= 0.1;
          popup.style.opacity = opacity;
          if (opacity <= 0) {
            clearInterval(interval);
            popup.removeChild(notification);
            if (popup.childNodes.length == 0) {
              popup.style.display = 'none';
            }
          }
        }, 200);
      }, sleep);
    }
  }, 25);
}
