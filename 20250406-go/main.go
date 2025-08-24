package main

import (
	"context"
	"fmt"
	"io"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func main() {
	// Create a new MCP server
	s := server.NewMCPServer(
		"read_ch32v003_datasheet",
		"0.0.1",
		server.WithResourceCapabilities(true, true),
		server.WithLogging(),
	)

	// CH32V003 Datasheet
	readDatasheetTool := mcp.NewTool("read_ch32v003_datasheet",
		mcp.WithDescription("マイコンCH32V003のデータシート"),
		mcp.WithString("mcu_name",
			mcp.Required(),
			mcp.Description("MCUの名前 (CH32V003)"),
			mcp.Enum("CH32V003"),
		),
	)

	s.AddTool(readDatasheetTool, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		// mcuName := request.Params.Arguments["mcu_name"].(string)
		f, err := os.Open("/Users/nnyn/ghq/github.com/74th/test-mcp_server/20250406-go/datasheet/ch32v003-ds.txt")
		if err != nil {
			return nil, fmt.Errorf("failed to open datasheet: %w", err)
		}
		defer f.Close()

		data, err := io.ReadAll(f)
		if err != nil {
			return nil, fmt.Errorf("failed to read datasheet: %w", err)
		}

		return mcp.NewToolResultText(string(data)), nil
	})

	// CH32V003 Development Guide Book
	readGuideBook := mcp.NewTool("read_ch32v003_development_guide_book",
		mcp.WithDescription(`マイコンCH32V003について書かれた開発ガイドブックのコンテンツを取得する。
フレームワークch32funや公式WCH SDKでの開発の仕方が書かれている。
以下の章に分かれている。
- PWM
- ADC
- I2C Master
- I2C Slave
このツールの引数chapterに上記の情報を与えるとその内容を取得できる`),
		mcp.WithString("chapter",
			mcp.Required(),
			mcp.Description("章の名前 (PWM, ADC, I2C Master, I2C Slave)"),
			mcp.Enum("PWM", "ADC", "I2C Master", "I2C Slave"),
		),
	)

	s.AddTool(readGuideBook, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		chapter := request.Params.Arguments["chapter"].(string)

		var filePath string
		switch chapter {
		case "PWM":
			filePath = "/Users/nnyn/ghq/github.com/74th/ch32v003-book/articles/7-pwm/README.md"
		case "ADC":
			filePath = "/Users/nnyn/ghq/github.com/74th/ch32v003-book/articles/8-adc/README.md"
		case "I2C Master":
			filePath = "/Users/nnyn/ghq/github.com/74th/ch32v003-book/articles/10-i2c_master/README.md"
		case "I2C Slave":
			filePath = "/Users/nnyn/ghq/github.com/74th/ch32v003-book/articles/11-i2c_slave/README.md"
		default:
			return nil, fmt.Errorf("unknown chapter: %s", chapter)
		}
		return mcp.NewToolResultText(filePath), nil
	})

	// // CH32V003 Reference Manual
	// referenceManualTool := mcp.NewTool("read_ch32v003_reference_manual",
	// 	mcp.WithDescription("CH32V003のリファレンスマニュアルを取得"),
	// 	mcp.WithString("mcu_name",
	// 		mcp.Required(),
	// 		mcp.Description("MCUの名前 (CH32V003)"),
	// 		mcp.Enum("CH32V003"),
	// 	),
	// )

	// s.AddTool(referenceManualTool, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// 	// mcuName := request.Params.Arguments["mcu_name"].(string)
	// 	f, err := os.Open("/Users/nnyn/ghq/github.com/74th/test-mcp_server/20250406-go/datasheet/ch32v003-rm.txt")
	// 	if err != nil {
	// 		return nil, fmt.Errorf("failed to open reference manual: %w", err)
	// 	}
	// 	defer f.Close()

	// 	data, err := io.ReadAll(f)
	// 	if err != nil {
	// 		return nil, fmt.Errorf("failed to read reference manual: %w", err)
	// 	}

	// 	return mcp.NewToolResultText(string(data)), nil
	// })

	// Start the server
	if err := server.ServeStdio(s); err != nil {
		fmt.Printf("Server error: %v\n", err)
	}
}
