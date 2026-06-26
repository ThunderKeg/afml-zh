(function () {
  var reader = document.getElementById("reader");
  var form = document.getElementById("jump-form");
  var input = document.getElementById("page-input");
  var title = document.getElementById("current-title");
  var links = Array.prototype.slice.call(document.querySelectorAll("[data-page]"));
  var maxPage = 393;

  function clampPage(value) {
    var page = parseInt(value, 10);
    if (!Number.isFinite(page)) return 1;
    return Math.min(Math.max(page, 1), maxPage);
  }

  function setActive(page) {
    links.forEach(function (link) {
      link.classList.toggle("active", link.dataset.page === String(page));
    });
  }

  function setPage(page, label, updateHash) {
    var nextPage = clampPage(page);
    reader.src = "book/afml.html#" + nextPage;
    input.value = nextPage;
    title.textContent = label || "PDF page " + nextPage;
    setActive(nextPage);
    if (updateHash !== false) {
      history.replaceState(null, "", "#page=" + nextPage);
    }
  }

  links.forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      setPage(link.dataset.page, link.textContent.trim(), true);
    });
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    setPage(input.value, null, true);
  });

  var match = window.location.hash.match(/page=(\d+)/);
  if (match) {
    setPage(match[1], null, false);
  } else {
    setPage(14, "Contents", false);
  }
})();
