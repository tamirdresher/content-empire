---
title: "Durable Task Framework + Aspire: Orchestrating Microservices"
date: 2025-07-25
author: "The Content Empire Team"
tags: ["dotnet", "microservices", "Aspire", "orchestration", "Durable-Task"]
description: "How to combine the Durable Task Framework with .NET Aspire to build reliable, observable microservice orchestrations that survive crashes and scale automatically."
---

Microservice orchestration is one of those problems that sounds simple until you're debugging a distributed workflow at 2 AM. Service A called Service B, which timed out, so Service A retried, but Service B actually succeeded the first time, and now you have duplicate orders.

The **Durable Task Framework (DTFx)** solves this by making workflows durable — they survive crashes, retries, and scaling events. Combined with **.NET Aspire** for local development and observability, you get a development experience that's almost unreasonably pleasant.

## The Problem: Fragile Orchestration

Consider a typical e-commerce order flow:

```
Order Placed → Validate Inventory → Charge Payment → Ship Order → Send Confirmation
```

In a naive implementation:

```csharp
// ❌ Fragile: What happens if the service crashes after payment but before shipping?
public async Task ProcessOrder(Order order)
{
    await inventoryService.Reserve(order.Items);
    await paymentService.Charge(order.PaymentInfo);
    // 💥 Crash here = charged but never shipped
    await shippingService.CreateShipment(order);
    await notificationService.SendConfirmation(order);
}
```

If the process crashes after charging the payment but before creating the shipment, you've charged the customer but never shipped their order. Retrying from scratch would double-charge them.

## Enter the Durable Task Framework

DTFx provides **durable execution** — your workflow state is automatically checkpointed. If the process crashes and restarts, it resumes exactly where it left off.

```csharp
// ✅ Durable: Survives crashes, retries, and scaling events
[DurableTask]
public class OrderOrchestration : TaskOrchestration<OrderResult, Order>
{
    public override async Task<OrderResult> RunAsync(
        TaskOrchestrationContext context, Order order)
    {
        // Each activity is checkpointed after completion
        var inventoryResult = await context.CallActivityAsync<InventoryResult>(
            nameof(ReserveInventory), order.Items);

        var paymentResult = await context.CallActivityAsync<PaymentResult>(
            nameof(ChargePayment), order.PaymentInfo);

        // If the process crashes HERE and restarts,
        // it knows inventory and payment are done.
        // It skips straight to shipping.

        var shipment = await context.CallActivityAsync<ShipmentResult>(
            nameof(CreateShipment), order);

        await context.CallActivityAsync(
            nameof(SendConfirmation), 
            new ConfirmationRequest(order, shipment));

        return new OrderResult(
            inventoryResult, paymentResult, shipment);
    }
}
```

### How Durability Works

The framework uses **event sourcing** under the hood:

```
Event Log:
1. OrchestratorStarted(orderId: "ORD-123")
2. ActivityScheduled("ReserveInventory")
3. ActivityCompleted("ReserveInventory", result: { reserved: true })
4. ActivityScheduled("ChargePayment")
5. ActivityCompleted("ChargePayment", result: { chargeId: "ch_abc" })
   💥 CRASH
   
   --- Process Restarts ---
   
6. OrchestratorStarted(orderId: "ORD-123")  ← Replays events 1-5
   → Skips ReserveInventory (already done)
   → Skips ChargePayment (already done)
7. ActivityScheduled("CreateShipment")       ← Resumes here
8. ActivityCompleted("CreateShipment", result: { trackingId: "TRK-456" })
9. ActivityScheduled("SendConfirmation")
10. ActivityCompleted("SendConfirmation")
11. OrchestratorCompleted(orderId: "ORD-123")
```

## Adding .NET Aspire: The Developer Experience Layer

Aspire handles the infrastructure and observability that DTFx doesn't cover. Together, they're a powerful combination.

### Setting Up the AppHost

```csharp
// AppHost/Program.cs
var builder = DistributedApplication.CreateBuilder(args);

// Infrastructure
var storage = builder.AddAzureStorage("storage")
    .RunAsEmulator();  // Local development uses emulator
var taskHub = storage.AddBlobs("task-hub");

// Services
var orderApi = builder.AddProject<Projects.OrderApi>("order-api")
    .WithReference(taskHub);

var inventoryService = builder.AddProject<Projects.InventoryService>("inventory")
    .WithReference(taskHub);

var paymentService = builder.AddProject<Projects.PaymentService>("payments")
    .WithReference(taskHub);

var shippingService = builder.AddProject<Projects.ShippingService>("shipping")
    .WithReference(taskHub);

builder.Build().Run();
```

### Configuring DTFx with Aspire

```csharp
// OrderApi/Program.cs
var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();  // Aspire service defaults

// Add Durable Task with Azure Storage backend
builder.Services.AddDurableTaskWorker(options =>
{
    options.AddOrchestration<OrderOrchestration>();
    options.AddActivity<ReserveInventory>();
    options.AddActivity<ChargePayment>();
    options.AddActivity<CreateShipment>();
    options.AddActivity<SendConfirmation>();
});

builder.Services.AddDurableTaskClient();

var app = builder.Build();

app.MapPost("/orders", async (
    Order order, DurableTaskClient client) =>
{
    var instanceId = await client.ScheduleNewOrchestrationInstanceAsync(
        nameof(OrderOrchestration), order);
    
    return Results.Accepted($"/orders/{instanceId}/status", 
        new { instanceId, status = "Processing" });
});

app.MapGet("/orders/{instanceId}/status", async (
    string instanceId, DurableTaskClient client) =>
{
    var metadata = await client.GetInstanceAsync(instanceId);
    return Results.Ok(new
    {
        instanceId,
        status = metadata?.RuntimeStatus.ToString(),
        createdAt = metadata?.CreatedAt,
        lastUpdatedAt = metadata?.LastUpdatedAt,
        output = metadata?.ReadOutputAs<OrderResult>()
    });
});

app.Run();
```

### Implementing Activities

Each activity is a focused, retriable unit of work:

```csharp
[DurableTask]
public class ReserveInventory : TaskActivity<List<OrderItem>, InventoryResult>
{
    private readonly InventoryClient _inventory;
    private readonly ILogger<ReserveInventory> _logger;

    public ReserveInventory(
        InventoryClient inventory, 
        ILogger<ReserveInventory> logger)
    {
        _inventory = inventory;
        _logger = logger;
    }

    public override async Task<InventoryResult> RunAsync(
        TaskActivityContext context, List<OrderItem> items)
    {
        _logger.LogInformation(
            "Reserving inventory for {Count} items, instance {Id}",
            items.Count, context.InstanceId);

        var result = await _inventory.ReserveAsync(items);
        
        if (!result.Success)
        {
            throw new InventoryException(
                $"Failed to reserve: {result.FailureReason}");
        }

        return result;
    }
}
```

## Advanced Patterns

### Fan-Out / Fan-In

Process multiple items in parallel and wait for all to complete:

```csharp
public override async Task<BatchResult> RunAsync(
    TaskOrchestrationContext context, BatchOrder batch)
{
    // Fan-out: process all items in parallel
    var tasks = batch.Items.Select(item =>
        context.CallActivityAsync<ItemResult>(
            nameof(ProcessItem), item));

    // Fan-in: wait for all to complete
    var results = await Task.WhenAll(tasks);

    // Aggregate results
    var summary = await context.CallActivityAsync<BatchSummary>(
        nameof(AggregateBatchResults), results);

    return new BatchResult(summary);
}
```

### Human Approval Workflow

Wait for external events (like a manager's approval):

```csharp
public override async Task<ApprovalResult> RunAsync(
    TaskOrchestrationContext context, PurchaseRequest request)
{
    if (request.Amount > 10_000)
    {
        // Send approval request notification
        await context.CallActivityAsync(
            nameof(SendApprovalRequest), request);

        // Wait up to 72 hours for approval
        var approval = await context.WaitForExternalEvent<ApprovalDecision>(
            "approval-response",
            TimeSpan.FromHours(72));

        if (approval?.Approved != true)
        {
            return ApprovalResult.Rejected(approval?.Reason);
        }
    }

    await context.CallActivityAsync(nameof(ProcessPurchase), request);
    return ApprovalResult.Approved();
}
```

### Retry Policies

Handle transient failures automatically:

```csharp
var retryOptions = new TaskOptions(
    new TaskRetryOptions(new RetryPolicy(
        maxNumberOfAttempts: 3,
        firstRetryInterval: TimeSpan.FromSeconds(5),
        backoffCoefficient: 2.0  // 5s, 10s, 20s
    )));

var result = await context.CallActivityAsync<PaymentResult>(
    nameof(ChargePayment), paymentInfo, retryOptions);
```

## Observability with Aspire Dashboard

One of the biggest wins of the Aspire + DTFx combination is observability. The Aspire dashboard gives you:

- **Distributed traces** — See the entire orchestration flow across services
- **Structured logs** — Every activity logs with correlation IDs
- **Metrics** — Orchestration duration, failure rates, queue depths
- **Resource health** — Status of all services, databases, and message queues

No additional configuration needed — Aspire's `AddServiceDefaults()` wires up OpenTelemetry automatically.

## When to Use This Stack

**Good fit:**
- Multi-step business workflows (orders, onboarding, data pipelines)
- Processes that must survive failures (payment flows, regulatory workflows)
- Long-running processes (hours to days, with human interaction)
- Fan-out/fan-in patterns (batch processing, parallel API calls)

**Overkill for:**
- Simple request-response APIs
- Fire-and-forget background jobs
- Single-service applications

## The Bottom Line

The Durable Task Framework removes the hardest part of distributed systems — making workflows reliable despite failures. Aspire removes the second hardest part — making the developer experience bearable.

Together, they let you build workflows that are durable, observable, and genuinely enjoyable to develop. Start with a simple orchestration and expand from there.

---

*Content Empire covers practical .NET and cloud development patterns. Follow for in-depth technical guides.*
