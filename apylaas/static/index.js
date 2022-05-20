const button = document.getElementById("toggle-uncallable");
const hiddenByDefaultPref = localStorage.getItem("hiddenByDefaultPref");

function hide() {
  Array.from(document.querySelectorAll(".index-list > li")).map((item) => {
    if (item.querySelector("span")) {
      item.style.display = "none";
    }
  });
  button.innerText = "Show Uncallable";
  localStorage.setItem("hiddenByDefaultPref", "1");
}

function show() {
  Array.from(document.querySelectorAll(".index-list > li")).map((item) => {
    if (item.querySelector("span")) {
      item.style.display = "list-item";
    }
  });
  button.innerText = "Hide Uncallable";
  localStorage.removeItem("hiddenByDefaultPref");
}

if (button) {
  button.addEventListener("click", (e) => {
    let shouldShow = !button.innerText.includes("Hide");

    if (shouldShow) {
      show();
    } else {
      hide();
    }
  });

  if (hiddenByDefaultPref) {
    hide();
  }
}
