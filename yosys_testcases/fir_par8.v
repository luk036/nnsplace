module fir_par #(
    parameter W = 16,
    parameter T = 8
)(
    input clk,
    input rst_n,
    input signed [W-1:0] data_in,
    output reg signed [W-1:0] data_out,
    output reg valid
);

    reg signed [W-1:0] sr [0:T-1];

    integer k;

    function signed [W-1:0] cf(input integer idx);
        integer v;
        begin
            v = ((idx * idx * 31 + idx * 17 + 5) % 257) - 128;
            cf = v;
        end
    endfunction

    genvar i;
    generate
        for (i = 0; i < T; i = i + 1) begin : chain
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n)
                    sr[i] <= 0;
                else if (i == 0)
                    sr[i] <= data_in;
                else
                    sr[i] <= sr[i-1];
            end
        end
    endgenerate

    wire signed [W+11:0] acc;
    reg signed [W+11:0] acc_r;

    always @(*) begin
        acc_r = 0;
        for (k = 0; k < T; k = k + 1)
            acc_r = acc_r + cf(k) * $signed(sr[k]);
    end
    assign acc = acc_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_out <= 0;
            valid <= 0;
        end else begin
            data_out <= acc[W+7:8];
            valid <= 1;
        end
    end
endmodule
