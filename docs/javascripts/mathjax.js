window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};

document$.subscribe(() => {
  const mathjax = window.MathJax;
  if (!mathjax || !mathjax.startup || !mathjax.typesetPromise) {
    return;
  }
  mathjax.startup.promise.then(() => {
    mathjax.startup.output.clearCache();
    mathjax.typesetClear();
    mathjax.texReset();
    mathjax.typesetPromise();
  });
});
