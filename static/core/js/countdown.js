document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-countdown-target]").forEach(function (el) {
    var target = new Date(el.dataset.countdownTarget).getTime();

    function tick() {
      var now = Date.now();
      var diff = target - now;

      if (diff <= 0) {
        el.textContent = "OPEN NOW";
        el.classList.add("text-success");
        var reopenNotice = document.querySelector("[data-countdown-open-badge]");
        if (reopenNotice) reopenNotice.classList.remove("d-none");
        clearInterval(timer);
        return;
      }

      var hours = Math.floor(diff / (1000 * 60 * 60));
      var minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      var seconds = Math.floor((diff % (1000 * 60)) / 1000);

      el.textContent =
        String(hours).padStart(2, "0") + ":" +
        String(minutes).padStart(2, "0") + ":" +
        String(seconds).padStart(2, "0");
    }

    tick();
    var timer = setInterval(tick, 1000);
  });
});
