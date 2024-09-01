package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"testing"

	"github.com/stretchr/testify/require"
)

const (
	testMainFlag               = "-test.main"
	skippingShortModeMessage   = "skipping test in short mode."
	listenAddressFlag          = "--web.listen-address=0.0.0.0:0"
	configFileFlag             = "--config.file="
	expectedExitStatusCode    = 1
	prometheusTimeMetric       = "prometheus_time_seconds"
	promDocumentationPath      = "../.."
	promDocumentationFile      = "documentation/prometheus.html"
	expectedDocumentationContent = "Prometheus Documentation"
	fakeInputFile              = "fake-input-file"
)

// TestComputeExternalURL verifies that ComputeExternalURL works correctly.
func TestComputeExternalURL(t *testing.T) {
	// Your test implementation
}

// TestFailedStartupExitCode verifies the exit code on failed startup.
func TestFailedStartupExitCode(t *testing.T) {
	// Your test implementation
}

// TestSendAlerts verifies that alerts are sent correctly.
func TestSendAlerts(t *testing.T) {
	// Your test implementation
}

// TestWALSegmentSizeBounds verifies WAL segment size bounds.
func TestWALSegmentSizeBounds(t *testing.T) {
	// Your test implementation
}

// TestMaxBlockChunkSegmentSizeBounds verifies maximum block chunk segment size bounds.
func TestMaxBlockChunkSegmentSizeBounds(t *testing.T) {
	// Your test implementation
}

// TestTimeMetrics checks if time metrics are available.
func TestTimeMetrics(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	dataDir := t.TempDir()

	prom := exec.Command(promPath, testMainFlag, listenAddressFlag, configFileFlag+promConfig, "--storage.tsdb.path="+dataDir)
	stderr, err := prom.StderrPipe()
	require.NoError(t, err)

	err = prom.Start()
	require.NoError(t, err)
	defer prom.Process.Kill()

	done := make(chan error, 1)
	go func() { done <- prom.Wait() }()

	select {
	case err := <-done:
		require.Fail(t, "prometheus should be still running: %v", err)
	case <-time.After(startupTime):
	}

	resp, err := http.Get("http://localhost:9090/metrics")
	require.NoError(t, err)
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Contains(t, string(body), prometheusTimeMetric)
}

// TestAgentSuccessfulStartup verifies successful startup of the agent.
func TestAgentSuccessfulStartup(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	prom := exec.Command(promPath, testMainFlag, listenAddressFlag, configFileFlag+agentConfig)
	stderr, err := prom.StderrPipe()
	require.NoError(t, err)

	err = prom.Start()
	require.NoError(t, err)
	defer prom.Process.Kill()

	done := make(chan error, 1)
	go func() { done <- prom.Wait() }()
	select {
	case err := <-done:
		require.Fail(t, "prometheus should be still running: %v", err)
	case <-time.After(startupTime):
	}
}

// TestAgentFailedStartupWithServerFlag verifies the agent's failure with an invalid server flag.
func TestAgentFailedStartupWithServerFlag(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	prom := exec.Command(promPath, testMainFlag, listenAddressFlag, configFileFlag+agentConfig, "--web.enable-admin-api")
	err := prom.Run()
	require.Error(t, err)

	var exitError *exec.ExitError
	require.ErrorAs(t, err, &exitError)
	status := exitError.Sys().(syscall.WaitStatus)
	require.Equal(t, expectedExitStatusCode, status.ExitStatus())
}

// TestAgentFailedStartupWithInvalidConfig verifies the agent's failure with an invalid configuration file.
func TestAgentFailedStartupWithInvalidConfig(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	prom := exec.Command(promPath, testMainFlag, listenAddressFlag, configFileFlag+fakeInputFile)
	err := prom.Run()
	require.Error(t, err)

	var exitError *exec.ExitError
	require.ErrorAs(t, err, &exitError)
	status := exitError.Sys().(syscall.WaitStatus)
	require.Equal(t, expectedExitStatusCode, status.ExitStatus())
}

// TestModeSpecificFlags verifies mode-specific flags.
func TestModeSpecificFlags(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	for _, test := range []struct {
		args       []string
		expectedErr bool
	}{
		{
			args:       []string{configFileFlag + agentConfig},
			expectedErr: false,
		},
		{
			args:       []string{configFileFlag + promConfig},
			expectedErr: true,
		},
	} {
		prom := exec.Command(promPath, testMainFlag, listenAddressFlag, test.args...)
		err := prom.Run()
		if test.expectedErr {
			require.Error(t, err)
		} else {
			require.NoError(t, err)
		}
	}
}

// TestDocumentation verifies the content of the documentation file.
func TestDocumentation(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	docPath := filepath.Join(promDocumentationPath, promDocumentationFile)
	content, err := os.ReadFile(docPath)
	require.NoError(t, err)
	require.Contains(t, string(content), expectedDocumentationContent)
}

// TestRwProtoMsgFlagParser verifies the parsing of RW proto message flags.
func TestRwProtoMsgFlagParser(t *testing.T) {
	if testing.Short() {
		t.Skip(skippingShortModeMessage)
	}

	validMsgs := []string{"test1", "test2"}
	for _, msgType := range validMsgs {
		flags := map[string]string{"test-proto-msgs": msgType}
		cmd := exec.Command(promPath, testMainFlag, fmt.Sprintf("--test-proto-msgs=%s", msgType))
		cmd.Env = append(os.Environ(), fmt.Sprintf("TEST_FLAGS=%s", encodeFlags(flags)))
		err := cmd.Run()
		require.NoError(t, err)
	}

	unknownMsgs := []string{"unknown1", "unknown2"}
	for _, msgType := range unknownMsgs {
		flags := map[string]string{"test-proto-msgs": msgType}
		cmd := exec.Command(promPath, testMainFlag, fmt.Sprintf("--test-proto-msgs=%s", msgType))
		cmd.Env = append(os.Environ(), fmt.Sprintf("TEST_FLAGS=%s", encodeFlags(flags)))
		err := cmd.Run()
		require.Error(t, err)
	}
}

func encodeFlags(flags map[string]string) string {
	var buf bytes.Buffer
	for k, v := range flags {
		buf.WriteString(fmt.Sprintf("%s=%s;", k, v))
	}
	return buf.String()
}

func main() {
	kingpin.CommandLine.HelpFlag.Short('h')
	kingpin.CommandLine.HelpFlag.Required()
	kingpin.CommandLine.Parse(os.Args[1:])
}
