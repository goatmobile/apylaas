import { createElement, h, render, Component } from "preact";

function getFullData() {
  let pastRuns = localStorage.getItem("past-runs");
  if (pastRuns) {
    return JSON.parse(pastRuns);
  } else {
    return {};
  }
}
function getRuns(name) {
  let fullData = getFullData();
  if (fullData[name]) {
    return fullData[name];
  } else {
    return [];
  }
}

function saveRun(name, inputs, output) {
  const data = getRuns();
  const fullData = getFullData();
  if (!fullData[name]) {
    fullData[name] = [];
  }
  fullData[name].push({
    inputs,
    output,
    run_at: new Date(),
  });
  localStorage.setItem("past-runs", JSON.stringify(fullData));
  return fullData[name].length - 1;
}

function saveRunInplace(name, idx, inputs, output) {
  const fullData = getFullData();
  const data = getRuns(name);
  fullData[name][idx] = {
    inputs,
    output,
    run_at: data[idx].run_at,
  };
  localStorage.setItem("past-runs", JSON.stringify(fullData));
}

const submit = document.getElementById("submit");
const form = document.getElementById("form");
const responseBox = document.getElementById("response");
const loadingIcon = document.getElementById("loading");
const lastOutputBox = document.getElementById("last-output-box");
const runtimeMsOutput = document.getElementById("runtimeMsOutput");
let counterInterval = null;
submit.addEventListener("click", async (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  const inputs = {};
  for (const [name, value] of fd.entries()) {
    if (value instanceof File) {
      // load bytes as base64
      inputs[name] = await value.arrayBuffer();
    } else {
      inputs[name] = value;
    }
  }
  for (const cb of Array.from(form.querySelectorAll("input[type=checkbox"))) {
    inputs[cb.name] = cb.checked;
    fd.append(cb.name, cb.checked);
  }
  console.log(inputs)
  lastOutputBox.style.display = "block";
  // document.body.querySelector("#input-pre").innerText = "2";
  render(<Args inputs={inputs} />, document.body.querySelector("#input-pre"));
  // document.body.querySelector("#input-pre").innerText = JSON.stringify(
  //   inputs,
  //   null,
  //   2
  // );
  responseBox.querySelector("#output-pre").innerText = "";

  if (counterInterval) {
    console.log("Clear");
    clearInterval(counterInterval);
  }

  const tickRateMs = 25;
  let time = 0;
  counterInterval = setInterval(() => {
    runtimeMsOutput.innerText = parseFloat(time / 1000).toFixed(1);
    time += tickRateMs;
  }, tickRateMs);

  const fn = window.location.href.split("/").slice(-1)[0];
  loadingIcon.style.display = "inline-block";
  let idx = saveRun(fn, inputs);
  renderPastRuns();
  console.log("starting ticker");

  fetch(`/api/${fn}`, {
    method: "POST",
    body: fd,
  }).then((r) => {
    clearInterval(counterInterval);
    r.text().then((response_data) => {
      loadingIcon.style.display = "none";
      let runtime = r.headers.get("X-Execution-Time-Ms");
      if (runtime) {
        const runtimeMs = JSON.parse(runtime);
        runtimeMsOutput.innerText = parseFloat(runtimeMs / 1000).toFixed(1);
      }
      document.body.querySelector("#output-pre").innerText = response_data;
      saveRunInplace(fn, idx, inputs, response_data);
      renderPastRuns();
    });
  });
});

// document.getElementById("clear-past-runs").addEventListener("click", (e) => {
//   const fullData = getFullData();
//   const fn = window.location.href.split("/").slice(-1)[0];
//   delete fullData[fn];
//   localStorage.setItem("past-runs", JSON.stringify(fullData));
//   renderPastRuns();
// });

function tryParse(text) {
  try {
    return JSON.parse(text);
  } catch (e) {
    return null;
  }
}

function renderPastRuns() {
  const runBody = document.getElementById("past-runs");
  runBody.innerHTML = "";
  const fn = window.location.href.split("/").slice(-1)[0];
  let pastRuns = getRuns(fn);
  render(<PastRuns runs={pastRuns} />, document.getElementById("past-runs"));
}

class Args extends Component {
  render() {
    console.log(this.props.inputs);
    const items = [];
    for (const name in this.props.inputs) {
      const arg = this.props.inputs[name];
      items.push(
        <p className="font-mono">
          {name}={JSON.stringify(arg)}
        </p>
      );
    }
    return <div>{items}</div>;
  }
}

class PastRuns extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hide: true,
    };
  }

  render() {
    const runs = this.props.runs;
    if (runs.length === 0) {
      return null;
    }

    const rows = [];
    for (const run of runs.reverse()) {
      let at = new Date(run.run_at);
      const out = tryParse(run.output);
      let error = false;
      if (out && out.message && out.exception) {
        error = true;
      }
      // if (error) {
      //   tr.classList.add("run-error");
      // }
      let output = <div>pending...</div>;
      if (run.output) {
        output = [
          <div className="uppercase text-sm font-semibold bg-blue-200 px-1 mt-1 rounded w-fit">
            output
          </div>,
          <pre className="max-w-md whitespace-pre-wrap max-h-96 overflow-y-auto">{run.output}</pre>,
        ];
      }
      const input = (
        <div>
          {/* <pre>{JSON.stringify(run.inputs, null, 2)}</pre> */}
          <Args inputs={run.inputs} />
        </div>
      );
      rows.push(
        <tr
          className={`even:bg-grey odd:bg-gray-200 ${
            error ? "even:bg-red-200 odd:bg-red-300" : ""
          }`}
        >
          <td className={`px-4 py-3`}>
            <div className="mb-2">
              <span className="text-white text-sm font-semibold bg-blue-500 px-2 py-1 rounded-lg">
                {at.toLocaleString()}
              </span>
            </div>
            {run.inputs ? (
              <div className="uppercase text-sm font-semibold bg-blue-200 px-1 rounded w-fit">
                Inputs
              </div>
            ) : null}
            {input}
            {output}
          </td>
        </tr>
      );
    }

    return (
      <div className="w-md mt-8">
        <div class="grid grid-cols-6">
          <p class="text-center col-span-5 font-bold uppercase">Past Runs</p>
          <button
            onClick={() => {
              const fullData = getFullData();
              const fn = window.location.href.split("/").slice(-1)[0];
              delete fullData[fn];
              localStorage.setItem("past-runs", JSON.stringify(fullData));
              renderPastRuns();
            }}
            class="bg-gray-500 hover:bg-gray-400 active:bg-gray-900 text-white font-bold text-sm w-fit px-3 py-1 border-b-4 border-gray-700 hover:border-gray-500 active:border-gray-800 rounded"
          >
            Clear
          </button>
        </div>
        <table class="mt-3 w-full">
          <tbody>{rows}</tbody>
        </table>
      </div>
    );
  }
}

renderPastRuns();
